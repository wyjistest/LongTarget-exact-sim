#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase3}"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-$ROOT/.paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization}"
GOAL="$ROOT/goal-final.md"
MANIFEST="$ROOT/paper/workload_manifest.tsv"
REPORT="$ROOT/paper/generalization_report.md"
ARTIFACT_MANIFEST="$ROOT/paper/phase3_artifact_manifest.tsv"
RUNS="$ROOT/paper/source_data/generalization_runs_pre_freeze.tsv"
PAIRS="$ROOT/paper/source_data/generalization_pairs_pre_freeze.tsv"
WORKLOADS="$ROOT/paper/source_data/generalization_workloads_pre_freeze.tsv"
GUARDS="$ROOT/paper/source_data/generalization_guards_pre_freeze.tsv"
FAILURES="$ROOT/paper/source_data/generalization_failures_pre_freeze.tsv"
MISMATCH_DETAILS="$ROOT/paper/source_data/generalization_mismatch_top5_pre_freeze.tsv"
INVENTORY="$ROOT/paper/artifact_inventory.tsv"
CLAIMS="$ROOT/paper/claim_evidence.tsv"
DRIVER="$ROOT/scripts/run_fasim_gasal2_paper_phase3.py"
SUMMARIZER="$ROOT/scripts/summarize_fasim_gasal2_paper_phase3.py"
COMPARATOR="$ROOT/scripts/compare_fasim_segmented_contract.py"
DRIVER_TEST="$ROOT/tests/check_run_fasim_gasal2_paper_phase3.py"
SUMMARY_TEST="$ROOT/tests/check_summarize_fasim_gasal2_paper_phase3.py"
COMPARATOR_TEST="$ROOT/tests/check_compare_fasim_segmented_contract.py"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for path in \
  "$GOAL" "$MANIFEST" "$REPORT" "$ARTIFACT_MANIFEST" \
  "$RUNS" "$PAIRS" "$WORKLOADS" "$GUARDS" "$FAILURES" "$MISMATCH_DETAILS" \
  "$INVENTORY" "$CLAIMS" "$DRIVER" "$SUMMARIZER" "$COMPARATOR" \
  "$DRIVER_TEST" "$SUMMARY_TEST" "$COMPARATOR_TEST" \
  "$ARTIFACT_ROOT/phase3-runs.tsv" \
  "$ARTIFACT_ROOT/phase3-pairs.tsv" \
  "$ARTIFACT_ROOT/phase3-guards.tsv" \
  "$ARTIFACT_ROOT/phase3-failures.tsv" \
  "$ARTIFACT_ROOT/phase3-artifacts.tsv"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 3 dependency: $path" >&2
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
  generalization_report.md \
  phase3_artifact_manifest.tsv \
  source_data/generalization_runs_pre_freeze.tsv \
  source_data/generalization_pairs_pre_freeze.tsv \
  source_data/generalization_workloads_pre_freeze.tsv \
  source_data/generalization_guards_pre_freeze.tsv \
  source_data/generalization_failures_pre_freeze.tsv \
  source_data/generalization_mismatch_top5_pre_freeze.tsv; do
  cmp "$ROOT/paper/$relative" "$WORK/generated-paper/$relative"
done

python3 - \
  "$ROOT" "$ARTIFACT_ROOT" "$GOAL" "$MANIFEST" "$REPORT" \
  "$ARTIFACT_MANIFEST" "$RUNS" "$PAIRS" "$WORKLOADS" "$GUARDS" \
  "$FAILURES" "$MISMATCH_DETAILS" "$INVENTORY" "$CLAIMS" <<'PY'
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
    workloads_path,
    guards_path,
    failures_path,
    mismatch_details_path,
    inventory_path,
    claims_path,
) = (Path(value).resolve() for value in sys.argv[1:])

runtime_commit = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
manifest_digest = "b099762257b60ce2922a7e19920bad30e05b9cdf2af4381c60596a41ca3cb7d3"
expected_counts = {
    "g01_malat1_5p_1024_chr11": 3,
    "g02_malat1_mid_2048_chr21": 3,
    "g03_malat1_3p_2812_chr22": 3,
    "g04_neat1_5p_2048_chr22": 3,
    "g05_neat1_mid_2812_chr11": 3,
    "g06_neat1_3p_1024_chr21": 3,
    "g07_kcnq1ot1_5p_2812_chr21": 3,
    "g08_kcnq1ot1_mid_1024_chr22": 3,
    "g09_kcnq1ot1_3p_2048_chr11": 3,
    "g10_h19_full_chr11": 1,
    "g11_h19_full_chr21": 1,
    "g12_h19_full_chr22": 1,
    "g13_meg3_full_chr11": 1,
}
expected_mismatches = {
    "g02_malat1_mid_2048_chr21": ("1", "0", "1"),
    "g09_kcnq1ot1_3p_2048_chr11": ("1", "1", "0"),
    "g12_h19_full_chr22": ("1", "0", "1"),
}
expected_guards = {
    "n01_malat1_full_guard": ("MALAT1", "8708"),
    "n02_neat1_full_guard": ("NEAT1", "22767"),
    "n03_kcnq1ot1_full_guard": ("KCNQ1OT1", "91667"),
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


if sha256(manifest_path) != manifest_digest:
    raise SystemExit("Phase 1 workload manifest digest drifted")

goal = goal_path.read_text(encoding="utf-8")
for phrase in (
    "active_phase = 4",
    "phase_3_status = pass",
    "last_completed_phase = 3",
    "last_decision = generalization_supported",
    "last_evidence_doc = paper/generalization_report.md",
    "last_test_command = make check-fasim-gasal2-paper-phase3",
    "last_commit = bench: complete preregistered short-query generalization panel",
):
    if phrase not in goal:
        raise SystemExit(f"goal-final Phase 3 state missing: {phrase}")

pair_fields, pairs = read_tsv(pairs_path)
required_pair_fields = {
    "pair_id_text", "workload_id", "role", "query_id", "query_length_nt",
    "fragment_position", "target_id", "target_region", "preset_id", "pair_id",
    "runtime_epoch", "runtime_commit", "comparator_version", "output_contract",
    "baseline_wall_seconds", "candidate_wall_seconds", "paired_speedup",
    "clustered_score_top5_equal", "clustered_stability_top5_equal",
    "clustered_nt_top5_equal", "boundary_ties_equal", "candidate_active_path",
    "fallbacks", "length_guard_fallbacks", "runtime_batch_fallbacks",
    "overflow_fallbacks", "oom", "status", "details_path", "pair_summary_path",
}
if not required_pair_fields.issubset(pair_fields):
    raise SystemExit("Phase 3 pair table is missing required telemetry fields")
if len(pairs) != 31 or Counter(row["workload_id"] for row in pairs) != Counter(expected_counts):
    raise SystemExit("Phase 3 pair count or preregistered workload set drifted")
if len({row["pair_id_text"] for row in pairs}) != len(pairs):
    raise SystemExit("duplicate Phase 3 pair ID")
if {row["preset_id"] for row in pairs} != {"gasal2_short_topk_v1"}:
    raise SystemExit("query-specific Phase 3 preset detected")

for row in pairs:
    pair_id = row["pair_id_text"]
    workload = row["workload_id"]
    expected_status = "mismatch" if workload in expected_mismatches else "clean"
    if row["runtime_epoch"] != "0" or row["runtime_commit"] != runtime_commit:
        raise SystemExit(f"runtime epoch mixing: {pair_id}")
    if row["comparator_version"] != "1" or row["output_contract"] != "fast_topk_score_stability_nt":
        raise SystemExit(f"comparator or output contract drift: {pair_id}")
    if row["status"] != expected_status:
        raise SystemExit(f"unexpected pair status: {pair_id}")
    observed_contract = (
        row["clustered_score_top5_equal"],
        row["clustered_stability_top5_equal"],
        row["clustered_nt_top5_equal"],
    )
    expected_contract = expected_mismatches.get(workload, ("1", "1", "1"))
    if observed_contract != expected_contract or row["boundary_ties_equal"] != "1":
        raise SystemExit(f"clustered tri-ranking or tie contract drift: {pair_id}")
    if row["candidate_active_path"] != "1":
        raise SystemExit(f"candidate GPU path inactive: {pair_id}")
    if any(row[field] != "0" for field in (
        "fallbacks", "length_guard_fallbacks", "runtime_batch_fallbacks",
        "overflow_fallbacks", "oom",
    )):
        raise SystemExit(f"fallback, overflow, or OOM in {pair_id}")
    baseline = float(row["baseline_wall_seconds"])
    candidate = float(row["candidate_wall_seconds"])
    speedup = float(row["paired_speedup"])
    if min(baseline, candidate, speedup) <= 0 or not all(map(math.isfinite, (baseline, candidate, speedup))):
        raise SystemExit(f"invalid timing in {pair_id}")
    if not math.isclose(speedup, baseline / candidate, rel_tol=1e-12, abs_tol=1e-12):
        raise SystemExit(f"paired speedup arithmetic mismatch: {pair_id}")
    for path_field in ("details_path", "pair_summary_path"):
        if Path(row[path_field]).is_absolute():
            raise SystemExit(f"machine-specific path exported in {pair_id}: {path_field}")
    pair_summary = artifact_root / row["pair_summary_path"]
    pair_config = pair_summary.with_name("pair-config.json")
    pair_complete = pair_summary.with_name("pair-complete.json")
    details = artifact_root / row["details_path"]
    for path in (pair_summary, pair_config, pair_complete, details):
        if not path.is_file():
            raise SystemExit(f"missing Phase 3 pair artifact: {path}")
    config = load_json(pair_config)
    complete = load_json(pair_complete)
    if config.get("config_digest_sha256") != canonical_config_digest(config):
        raise SystemExit(f"pair config digest mismatch: {pair_id}")
    if complete.get("config_digest_sha256") != config.get("config_digest_sha256"):
        raise SystemExit(f"pair completion/config mismatch: {pair_id}")
    if complete.get("summary_sha256") != sha256(pair_summary):
        raise SystemExit(f"pair summary digest mismatch: {pair_id}")

_, runs = read_tsv(runs_path)
if len(runs) != 91:
    raise SystemExit(f"expected 91 Phase 3 run receipts, found {len(runs)}")
if Counter(row["warmup"] for row in runs) != Counter({"0": 65, "1": 26}):
    raise SystemExit("Phase 3 timed/warmup/preflight run counts drifted")
if any(Path(row["receipt_path"]).is_absolute() for row in runs):
    raise SystemExit("machine-specific run receipt path exported")

_, workloads = read_tsv(workloads_path)
if len(workloads) != 13 or Counter(row["status"] for row in workloads) != Counter({"clean": 10, "mismatch": 3}):
    raise SystemExit("Phase 3 workload decision counts drifted")
for row in workloads:
    workload = row["workload_id"]
    if row["valid_pairs"] != str(expected_counts[workload]) or row["repeat_consistent"] != "1":
        raise SystemExit(f"repeat gate failed: {workload}")
    if row["fallbacks_total"] != "0" or row["oom_total"] != "0":
        raise SystemExit(f"workload fallback/OOM gate failed: {workload}")
if len({row["preset_id"] for row in workloads}) != 1:
    raise SystemExit("workload summary contains query-specific presets")

_, guards = read_tsv(guards_path)
if len(guards) != 3 or {row["workload_id"] for row in guards} != set(expected_guards):
    raise SystemExit("Phase 3 full-length guard set drifted")
for row in guards:
    if (row["query_id"], row["query_length_nt"]) != expected_guards[row["workload_id"]]:
        raise SystemExit(f"guard identity/length drift: {row['workload_id']}")
    if (
        row["supported"] != "0"
        or row["reason"] != "query_length_contract"
        or row["gpu_fast_path_executed"] != "0"
        or row["status"] != "guarded"
    ):
        raise SystemExit(f"fail-closed guard failed: {row['workload_id']}")
    if Path(row["receipt_path"]).is_absolute():
        raise SystemExit(f"machine-specific guard path exported: {row['workload_id']}")

_, failures = read_tsv(failures_path)
if failures:
    raise SystemExit(f"unexpected Phase 3 technical failures: {len(failures)}")

detail_fields, mismatch_details = read_tsv(mismatch_details_path)
required_detail_fields = {
    "pair_id_text", "workload_id", "pair_status", "side", "kind", "mode",
    "rank", "cluster_id", "TFO sequence", "TTS sequence",
}
if not required_detail_fields.issubset(detail_fields) or len(mismatch_details) != 420:
    raise SystemExit("Phase 3 mismatch top5 detail schema/count drifted")
details_by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in mismatch_details:
    details_by_pair[row["pair_id_text"]].append(row)
if set(details_by_pair) != {row["pair_id_text"] for row in pairs if row["status"] == "mismatch"}:
    raise SystemExit("not every mismatch pair has detail authority")
for pair_id, rows in details_by_pair.items():
    if {row["side"] for row in rows} != {"baseline", "candidate"}:
        raise SystemExit(f"mismatch side coverage failed: {pair_id}")
    if {row["kind"] for row in rows} != {"raw", "clustered"}:
        raise SystemExit(f"mismatch raw/clustered coverage failed: {pair_id}")
    if {row["mode"] for row in rows} != {"score", "stability", "nt"}:
        raise SystemExit(f"mismatch ranking coverage failed: {pair_id}")
    if any(not row["rank"] or not row["cluster_id"] for row in rows):
        raise SystemExit(f"mismatch rank/cluster evidence missing: {pair_id}")

artifact_fields, artifacts = read_tsv(artifact_manifest_path)
if artifact_fields != ["artifact_path", "size_bytes", "sha256"] or len(artifacts) != 1367:
    raise SystemExit("Phase 3 artifact manifest schema/count drifted")
if sha256(artifact_manifest_path) != "ef16dbbb7250304a46ac28d2584bedfd1186e3497fd7bc8038b3b004edc52b40":
    raise SystemExit("Phase 3 artifact manifest digest drifted")
for row in artifacts:
    path = artifact_root / row["artifact_path"]
    if not path.is_file():
        raise SystemExit(f"missing immutable Phase 3 artifact: {path}")
    if path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
        raise SystemExit(f"immutable Phase 3 artifact digest mismatch: {path}")

report = report_path.read_text(encoding="utf-8")
for phrase in (
    "decision = generalization_supported",
    "clean_workloads = 10/13",
    "bootstrap_interval = deferred_to_phase_5",
    "The three mismatch workloads remain part of the evidence package.",
    "All three full-length negative controls were rejected",
):
    if phrase not in report:
        raise SystemExit(f"Phase 3 report missing: {phrase}")

_, claims = read_tsv(claims_path)
claim_map = {row["claim_id"]: row for row in claims}
for claim_id in ("C2", "C3"):
    row = claim_map[claim_id]
    if row["current_evidence_path"] != "paper/generalization_report.md" or row["status"] != "supported":
        raise SystemExit(f"claim ledger not promoted from Phase 3 evidence: {claim_id}")

_, inventory = read_tsv(inventory_path)
inventory_paths = {row["artifact_path"] for row in inventory}
required_inventory = {
    "paper/generalization_report.md",
    "paper/phase3_artifact_manifest.tsv",
    "paper/source_data/generalization_runs_pre_freeze.tsv",
    "paper/source_data/generalization_pairs_pre_freeze.tsv",
    "paper/source_data/generalization_workloads_pre_freeze.tsv",
    "paper/source_data/generalization_guards_pre_freeze.tsv",
    "paper/source_data/generalization_failures_pre_freeze.tsv",
    "paper/source_data/generalization_mismatch_top5_pre_freeze.tsv",
}
if not required_inventory.issubset(inventory_paths):
    raise SystemExit("Phase 3 generated evidence is missing from artifact inventory")

print("GASAL2 paper Phase 3 gate OK")
print("decision=generalization_supported")
print("clean_workloads=10/13")
print("mismatch_workloads=3")
print("guarded_full_length_queries=3")
print("fallbacks=0")
print("oom=0")
PY

echo "GASAL2 paper Phase 3 checks OK"
