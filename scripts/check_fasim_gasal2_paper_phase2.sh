#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase2}"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-$ROOT/.paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core}"
GOAL="$ROOT/goal-final.md"
MANIFEST="$ROOT/paper/workload_manifest.tsv"
REPORT="$ROOT/paper/core_benchmark_report.md"
ARTIFACT_MANIFEST="$ROOT/paper/phase2_artifact_manifest.tsv"
RUNS="$ROOT/paper/source_data/core_benchmark_runs_pre_freeze.tsv"
PAIRS="$ROOT/paper/source_data/core_benchmark_pairs_pre_freeze.tsv"
FAILURES="$ROOT/paper/source_data/core_benchmark_failures_pre_freeze.tsv"
SUMMARY="$ROOT/paper/source_data/core_benchmark_summary_pre_freeze.tsv"
OPERATING="$ROOT/paper/source_data/core_operating_envelope_pre_freeze.tsv"
INVENTORY="$ROOT/paper/artifact_inventory.tsv"
DRIVER="$ROOT/scripts/run_fasim_gasal2_paper_phase2.py"
SUMMARIZER="$ROOT/scripts/summarize_fasim_gasal2_paper_phase2.py"
DRIVER_TEST="$ROOT/tests/check_run_fasim_gasal2_paper_phase2.py"
SUMMARY_TEST="$ROOT/tests/check_summarize_fasim_gasal2_paper_phase2.py"
COMPARATOR_TEST="$ROOT/tests/check_compare_fasim_gasal2_long_query_integrated.py"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for path in \
  "$GOAL" "$MANIFEST" "$REPORT" "$ARTIFACT_MANIFEST" \
  "$RUNS" "$PAIRS" "$FAILURES" "$SUMMARY" "$OPERATING" "$INVENTORY" \
  "$DRIVER" "$SUMMARIZER" "$DRIVER_TEST" "$SUMMARY_TEST" "$COMPARATOR_TEST" \
  "$ARTIFACT_ROOT/phase2-runs.tsv" \
  "$ARTIFACT_ROOT/phase2-pairs.tsv" \
  "$ARTIFACT_ROOT/phase2-failures.tsv" \
  "$ARTIFACT_ROOT/phase2-artifacts.tsv"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 2 dependency: $path" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/generated-paper"

python3 "$DRIVER_TEST"
python3 "$SUMMARY_TEST"
python3 "$COMPARATOR_TEST"
python3 "$SUMMARIZER" \
  --artifact-root "$ARTIFACT_ROOT" \
  --paper-dir "$WORK/generated-paper" >"$WORK/summarize.stdout"

for relative in \
  core_benchmark_report.md \
  phase2_artifact_manifest.tsv \
  source_data/core_benchmark_runs_pre_freeze.tsv \
  source_data/core_benchmark_pairs_pre_freeze.tsv \
  source_data/core_benchmark_failures_pre_freeze.tsv \
  source_data/core_benchmark_summary_pre_freeze.tsv \
  source_data/core_operating_envelope_pre_freeze.tsv; do
  cmp "$ROOT/paper/$relative" "$WORK/generated-paper/$relative"
done

python3 - \
  "$ROOT" "$ARTIFACT_ROOT" "$GOAL" "$MANIFEST" "$REPORT" \
  "$ARTIFACT_MANIFEST" "$RUNS" "$PAIRS" "$FAILURES" "$SUMMARY" \
  "$OPERATING" "$INVENTORY" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


(
    root,
    artifact_root,
    goal_path,
    manifest_path,
    report_path,
    artifact_manifest_path,
    runs_path,
    pairs_path,
    failures_path,
    summary_path,
    operating_path,
    inventory_path,
) = (Path(value).resolve() for value in sys.argv[1:])
runtime_commit = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
binary_digest = "613b24d9190b8b931661fce231ded6662d2b2b3e5772262310e069c15f191cc8"
manifest_digest = "b099762257b60ce2922a7e19920bad30e05b9cdf2af4381c60596a41ca3cb7d3"
expected_pairs = {
    "c1_h19_chr21_chr22_fast_topk": 5,
    "c4_h19_chr21_two_slot": 5,
    "c4_h19_chr22_two_slot": 5,
    "c7_kcnq_max8_chr22": 3,
}
expected_contracts = {
    "c1_h19_chr21_chr22_fast_topk": "fast_topk_score_stability_nt",
    "c4_h19_chr21_two_slot": "fast_topk_score_stability_nt",
    "c4_h19_chr22_two_slot": "fast_topk_score_stability_nt",
    "c7_kcnq_max8_chr22": "shifted_grid_bounded_full_rows",
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


def canonical_digest(payload: dict[str, object]) -> str:
    comparable = dict(payload)
    comparable.pop("config_digest_sha256", None)
    encoded = json.dumps(comparable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


if sha256(manifest_path) != manifest_digest:
    raise SystemExit("Phase 1 workload manifest digest drifted")

goal = goal_path.read_text(encoding="utf-8")
state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
try:
    active_phase = int(state.get("active_phase", "-1"))
    last_completed_phase = int(state.get("last_completed_phase", "-1"))
except ValueError as exc:
    raise SystemExit("goal phase state is not numeric") from exc
if active_phase < 3 or last_completed_phase < 2:
    raise SystemExit("goal state has regressed before completed Phase 2")
if state.get("phase_2_status") != "pass":
    raise SystemExit("goal-final.md does not record phase_2_status = pass")
if active_phase == 3:
    phase2_terminal_state = {
        "last_completed_phase": "2",
        "last_decision": "paper_core_paired_benchmarks_collected",
        "last_evidence_doc": "paper/core_benchmark_report.md",
        "last_test_command": "make check-fasim-gasal2-paper-phase2",
        "last_commit": "bench: collect paired paper benchmarks for core GASAL2 claims",
    }
    for key, expected in phase2_terminal_state.items():
        if state.get(key) != expected:
            raise SystemExit(
                f"goal Phase 2 terminal state mismatch for {key}: "
                f"{state.get(key)!r} != {expected!r}"
            )

pair_fields, pairs = read_tsv(pairs_path)
required_pair_fields = {
    "pair_id_text",
    "workload_id",
    "pair_id",
    "runtime_epoch",
    "runtime_commit",
    "comparator_version",
    "output_contract",
    "baseline_wall_seconds",
    "candidate_wall_seconds",
    "paired_speedup",
    "candidate_active_path",
    "candidate_worker_count",
    "candidate_gpu_ids",
    "candidate_lifecycle_count",
    "candidate_slot_rotation_clean",
    "candidate_host_overlap_seconds",
    "candidate_state_order_allocation_violations",
    "archive_restore_clean",
    "exact_work_equal",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "full_output_byte_equal",
    "missing_rows",
    "extra_rows",
    "fallbacks",
    "oom",
    "status",
    "decision",
    "pair_summary_path",
}
if not required_pair_fields.issubset(pair_fields):
    raise SystemExit("Phase 2 pair table is missing required telemetry fields")
if len(pairs) != 18:
    raise SystemExit(f"expected 18 Phase 2 pairs, found {len(pairs)}")
counts = Counter(row["workload_id"] for row in pairs)
if dict(counts) != expected_pairs:
    raise SystemExit(f"Phase 2 pair counts mismatch: {dict(counts)}")
if len({row["pair_id_text"] for row in pairs}) != len(pairs):
    raise SystemExit("duplicate Phase 2 pair ID")

for row in pairs:
    pair_id = row["pair_id_text"]
    workload = row["workload_id"]
    if row["runtime_epoch"] != "0" or row["runtime_commit"] != runtime_commit:
        raise SystemExit(f"runtime epoch mixing in {pair_id}")
    if row["comparator_version"] != "3":
        raise SystemExit(f"non-authoritative comparator version in {pair_id}")
    if row["output_contract"] != expected_contracts[workload]:
        raise SystemExit(f"output contract mismatch in {pair_id}")
    if row["status"] != "clean":
        raise SystemExit(f"non-clean pair in authority table: {pair_id}")
    if any(row[field] != "1" for field in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal")):
        raise SystemExit(f"three-ranking top5 contract failed: {pair_id}")
    if row["fallbacks"] != "0" or row["oom"] != "0":
        raise SystemExit(f"fallback or OOM in {pair_id}")
    baseline = float(row["baseline_wall_seconds"])
    candidate = float(row["candidate_wall_seconds"])
    speedup = float(row["paired_speedup"])
    if min(baseline, candidate, speedup) <= 0 or not all(map(math.isfinite, (baseline, candidate, speedup))):
        raise SystemExit(f"invalid timing in {pair_id}")
    if not math.isclose(speedup, baseline / candidate, rel_tol=1e-12, abs_tol=1e-12):
        raise SystemExit(f"speedup arithmetic mismatch in {pair_id}")
    if workload == "c1_h19_chr21_chr22_fast_topk":
        if (
            row["decision"] != "formal_topk_contract_clean"
            or row["candidate_active_path"] != "1"
            or row["candidate_worker_count"] != "2"
            or row["candidate_gpu_ids"] != "0,1"
        ):
            raise SystemExit(f"C1 active-path placement gate failed: {pair_id}")
    elif workload.startswith("c4_"):
        if (
            row["decision"] != "two_slot_contract_clean"
            or int(row["candidate_lifecycle_count"]) <= 0
            or row["candidate_slot_rotation_clean"] != "1"
            or float(row["candidate_host_overlap_seconds"]) <= 0
            or row["candidate_state_order_allocation_violations"] != "0"
        ):
            raise SystemExit(f"C4 two-slot lifecycle gate failed: {pair_id}")
    elif workload == "c7_kcnq_max8_chr22":
        if (
            row["decision"] != "paired_integrated_contract_clean"
            or row["full_output_byte_equal"] != "1"
            or row["missing_rows"] != "0"
            or row["extra_rows"] != "0"
            or row["archive_restore_clean"] != "1"
            or row["exact_work_equal"] != "1"
        ):
            raise SystemExit(f"C7 bounded full-row contract failed: {pair_id}")

    summary_relative = Path(row["pair_summary_path"])
    if summary_relative.is_absolute():
        raise SystemExit(f"machine-specific pair path was exported: {pair_id}")
    summary_file = artifact_root / summary_relative
    complete_file = summary_file.with_name("pair-complete.json")
    config_file = summary_file.with_name("pair-config.json")
    for path in (summary_file, complete_file, config_file):
        if not path.is_file():
            raise SystemExit(f"missing pair receipt file: {path}")
    complete = load_json(complete_file)
    config = load_json(config_file)
    if complete.get("summary_sha256") != sha256(summary_file):
        raise SystemExit(f"pair summary digest mismatch: {pair_id}")
    if config.get("config_digest_sha256") != canonical_digest(config):
        raise SystemExit(f"pair config digest mismatch: {pair_id}")
    for mode in ("baseline", "candidate"):
        component = artifact_root / str(config[f"{mode}_run_id"]) / "run-complete.json"
        if sha256(component) != config.get(f"{mode}_receipt_sha256"):
            raise SystemExit(f"pair component digest mismatch: {pair_id} {mode}")

run_fields, runs = read_tsv(runs_path)
if len(runs) != 44:
    raise SystemExit(f"expected 44 completed Phase 2 runs including warmups, found {len(runs)}")
if len({row["run_id"] for row in runs}) != len(runs):
    raise SystemExit("duplicate Phase 2 run ID")
warmups: defaultdict[str, set[str]] = defaultdict(set)
for row in runs:
    run_id = row["run_id"]
    if row["status"] != "complete" or row["runtime_epoch"] != "0":
        raise SystemExit(f"incomplete or mixed-epoch run: {run_id}")
    if len(row["config_digest_sha256"]) != 64:
        raise SystemExit(f"missing config digest: {run_id}")
    receipt_relative = Path(row["receipt_path"])
    if receipt_relative.is_absolute():
        raise SystemExit(f"machine-specific run path was exported: {run_id}")
    receipt_path = artifact_root / receipt_relative
    run_dir = receipt_path.parent
    receipt = load_json(receipt_path)
    config = load_json(run_dir / "run-config.json")
    if config.get("runtime_commit") != runtime_commit or config.get("runtime_epoch") != 0:
        raise SystemExit(f"run runtime mismatch: {run_id}")
    if config.get("binary_sha256") != binary_digest:
        raise SystemExit(f"run binary digest mismatch: {run_id}")
    if config.get("config_digest_sha256") != canonical_digest(config):
        raise SystemExit(f"run config digest mismatch: {run_id}")
    if receipt.get("config_digest_sha256") != config.get("config_digest_sha256"):
        raise SystemExit(f"run receipt/config mismatch: {run_id}")
    for field, filename in (
        ("summary_sha256", "summary.json"),
        ("stdout_sha256", "stdout.log"),
        ("stderr_sha256", "stderr.log"),
    ):
        if receipt.get(field) != sha256(run_dir / filename):
            raise SystemExit(f"run receipt digest mismatch: {run_id} {filename}")
    for metric in (
        "gpu_memory_peak_mib",
        "gpu_temperature_peak_c",
        "gpu_power_peak_w",
        "max_rss_kb",
        "wall_seconds",
    ):
        if row.get(metric, "") in {"", "NA"}:
            raise SystemExit(f"missing Phase 2 run telemetry: {run_id} {metric}")
    if row["warmup"] == "1":
        warmups[row["workload_id"]].add(row["mode"])
if set(warmups) != set(expected_pairs) or any(modes != {"baseline", "candidate"} for modes in warmups.values()):
    raise SystemExit(f"warm-up coverage mismatch: {dict(warmups)}")

for run_dir in sorted(artifact_root.glob("c7_kcnq_max8_chr22__*__*__0")):
    integrated_config = run_dir / "output" / "run-config.json"
    if not integrated_config.is_file():
        raise SystemExit(f"missing C7 integrated config: {run_dir}")
    payload = load_json(integrated_config)
    if (
        payload.get("max_segments") != 8
        or payload.get("segment_len") != 2048
        or payload.get("segment_overlap") != 512
        or payload.get("grid_shifts") != [0, 256]
    ):
        raise SystemExit(f"C7 exceeded bounded max8 contract: {run_dir}")
if any("fullquery" in path.name.lower() for path in artifact_root.iterdir()):
    raise SystemExit("prohibited full-query run found in Phase 2 artifact root")

failure_fields, failures = read_tsv(failures_path)
if not failures:
    raise SystemExit("Phase 2 failure inventory unexpectedly empty")
if not any(row["reason"] == "pair_comparator_failure" for row in failures):
    raise SystemExit("retained C7 comparator technical failure is missing")
if not any(row["reason"] == "superseded_derived_pair" for row in failures):
    raise SystemExit("superseded C1 mismatch receipts are missing")
for row in failures:
    path = Path(row["artifact_path"])
    if path.is_absolute() or not (artifact_root / path).exists():
        raise SystemExit(f"invalid retained failure path: {path}")

summary_fields, summaries = read_tsv(summary_path)
if len(summaries) != 4 or {row["workload_id"] for row in summaries} != set(expected_pairs):
    raise SystemExit("Phase 2 summary workload coverage mismatch")
if any(int(row["valid_pairs"]) != expected_pairs[row["workload_id"]] for row in summaries):
    raise SystemExit("Phase 2 summary valid-pair count mismatch")
if any(row["top5_contract_clean"] != "1" or row["fallbacks_total"] != "0" or row["oom_total"] != "0" for row in summaries):
    raise SystemExit("Phase 2 summary correctness/fallback gate failed")

_, operating = read_tsv(operating_path)
required_operating = {
    "chr22_full",
    "chr1_full",
    "malat1_first8",
    "neat1_first64",
    "h19_short_integrated",
}
if {row["workload_id"] for row in operating} != required_operating:
    raise SystemExit("descriptive operating-envelope coverage mismatch")
if any(row["n"] != "1" or row["source_class"] != "committed_historical_artifact" for row in operating):
    raise SystemExit("descriptive operating-envelope provenance mismatch")

raw_manifest = artifact_root / "phase2-artifacts.tsv"
if artifact_manifest_path.read_bytes() != raw_manifest.read_bytes():
    raise SystemExit("tracked Phase 2 artifact manifest differs from raw manifest")
artifact_fields, artifact_rows = read_tsv(artifact_manifest_path)
if artifact_fields != ["artifact_path", "size_bytes", "sha256"]:
    raise SystemExit("Phase 2 artifact manifest schema mismatch")
listed_paths: set[str] = set()
for row in artifact_rows:
    relative = row["artifact_path"]
    if relative in listed_paths:
        raise SystemExit(f"duplicate artifact manifest path: {relative}")
    listed_paths.add(relative)
    path = artifact_root / relative
    if not path.is_file() or path.stat().st_size != int(row["size_bytes"]):
        raise SystemExit(f"artifact manifest size/path mismatch: {relative}")
    if sha256(path) != row["sha256"]:
        raise SystemExit(f"artifact manifest digest mismatch: {relative}")
actual_paths = {
    path.relative_to(artifact_root).as_posix()
    for path in artifact_root.rglob("*")
    if path.is_file() and path != raw_manifest
}
if listed_paths != actual_paths:
    missing = sorted(actual_paths - listed_paths)[:5]
    extra = sorted(listed_paths - actual_paths)[:5]
    raise SystemExit(f"artifact manifest coverage mismatch missing={missing} extra={extra}")

_, inventory = read_tsv(inventory_path)
inventory_by_path = {row["artifact_path"]: row for row in inventory}
for path in (
    report_path,
    artifact_manifest_path,
    runs_path,
    pairs_path,
    failures_path,
    summary_path,
    operating_path,
):
    relative = path.relative_to(root).as_posix()
    row = inventory_by_path.get(relative)
    if not row or row["exists"] != "1" or row["sha256"] != sha256(path):
        raise SystemExit(f"artifact inventory missing/stale Phase 2 output: {relative}")
    if row["source_classification"] != "reproduced_current_epoch":
        raise SystemExit(f"Phase 2 output source class mismatch: {relative}")

report = report_path.read_text(encoding="utf-8")
for phrase in (
    "Phase 2 core paired benchmarks",
    "bootstrap_interval = deferred_to_phase_5",
    "full 121-segment KCNQ1OT1 and full hg38 were not run",
    "core_benchmark_pairs_pre_freeze.tsv",
):
    if phrase not in report:
        raise SystemExit(f"Phase 2 report missing: {phrase}")

print(
    "paper Phase 2 OK: "
    f"pairs={len(pairs)} runs={len(runs)} retained_failures={len(failures)} "
    f"artifact_files={len(artifact_rows)} runtime_epoch=0 full121_runs=0"
)
PY
