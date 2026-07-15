#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase1}"
GOAL="$ROOT/goal-final.md"
PROTOCOL="$ROOT/paper/benchmark_protocol.md"
MANIFEST="$ROOT/paper/workload_manifest.tsv"
MANIFEST_RECEIPT="$ROOT/paper/workload_manifest.sha256"
ARTIFACTS="$ROOT/paper/artifact_inventory.tsv"
GAPS="$ROOT/paper/gap_register.tsv"
CLAIMS="$ROOT/paper/claim_evidence.tsv"
HARNESS="$ROOT/scripts/run_fasim_gasal2_paper_benchmarks.sh"
HARNESS_PY="$ROOT/scripts/run_fasim_gasal2_paper_benchmarks.py"
ENV_CAPTURE="$ROOT/scripts/capture_fasim_gasal2_paper_environment.py"
COLLECTOR="$ROOT/scripts/collect_fasim_gasal2_paper_run.py"
HARNESS_TEST="$ROOT/tests/check_run_fasim_gasal2_paper_benchmarks.py"
BINARY="$ROOT/.tmp/fasim_longtarget_gasal2_direct"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$GOAL" \
  "$PROTOCOL" \
  "$MANIFEST" \
  "$MANIFEST_RECEIPT" \
  "$ARTIFACTS" \
  "$GAPS" \
  "$CLAIMS" \
  "$HARNESS" \
  "$HARNESS_PY" \
  "$ENV_CAPTURE" \
  "$COLLECTOR" \
  "$HARNESS_TEST" \
  "$BINARY" \
  "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 1 dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$HARNESS_TEST"
python3 "$ENV_CAPTURE" --output "$WORK/environment.json"
bash "$HARNESS" \
  --dry-run \
  --manifest "$MANIFEST" \
  --binary "$BINARY" \
  --seed 20260715 >"$WORK/dry-run.json"

python3 - \
  "$ROOT" "$GOAL" "$PROTOCOL" "$MANIFEST" "$MANIFEST_RECEIPT" \
  "$ARTIFACTS" "$GAPS" "$CLAIMS" "$HARNESS" "$HARNESS_PY" \
  "$ENV_CAPTURE" "$COLLECTOR" "$HARNESS_TEST" "$BINARY" \
  "$MAKEFILE" "$WORK/environment.json" "$WORK/dry-run.json" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


(
    root,
    goal_path,
    protocol_path,
    manifest_path,
    manifest_receipt_path,
    artifacts_path,
    gaps_path,
    claims_path,
    harness_path,
    harness_py_path,
    environment_capture_path,
    collector_path,
    harness_test_path,
    binary_path,
    makefile_path,
    environment_path,
    dry_run_path,
) = (Path(value) for value in sys.argv[1:])

baseline = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
manifest_digest = "b099762257b60ce2922a7e19920bad30e05b9cdf2af4381c60596a41ca3cb7d3"
seed = 20260715
expected_header = [
    "workload_id",
    "claim_id",
    "family",
    "role",
    "query_id",
    "query_path",
    "query_sha256",
    "query_start_nt",
    "query_end_nt",
    "query_length_nt",
    "fragment_position",
    "target_id",
    "target_path",
    "target_sha256",
    "target_region",
    "rule",
    "baseline_mode",
    "candidate_mode",
    "output_contract",
    "required_pairs",
    "requires_gpu_count",
    "max_wall_seconds",
    "preset_id",
    "preregistered",
    "adapter_id",
]
allowed_roles = {
    "core",
    "generalization_core",
    "breadth",
    "negative_control",
    "descriptive",
}
allowed_contracts = {
    "fast_topk_score_stability_nt",
    "full_tfosorted_rowset",
    "preflight_guard_only",
    "archive_restore_only",
    "shifted_grid_bounded_full_rows",
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
        rows = list(reader)
    return reader.fieldnames, rows


def resolve_manifest_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


protocol = protocol_path.read_text(encoding="utf-8")
for phrase in (
    "protocol_version = 2",
    "paper_runtime_epoch = 0",
    baseline,
    f"paired_order_seed = {seed}",
    f"workload_manifest_sha256 = {manifest_digest}",
    "make build-fasim-gasal2",
    "one worker per GPU",
    "Warm-up",
    "AB/BA",
    "Timing boundary",
    ".paper-artifacts",
):
    if phrase not in protocol:
        raise SystemExit(f"paper benchmark protocol missing: {phrase}")
protocol_lower = protocol.lower()
for phrase in (
    "## telemetry",
    "## correctness contracts",
    "fallback",
    "## repeat counts",
    "## exclusions and reruns",
    "## timeouts",
    "immutable manifest",
):
    if phrase not in protocol_lower:
        raise SystemExit(f"paper benchmark protocol missing: {phrase}")

actual_manifest_digest = sha256(manifest_path)
if actual_manifest_digest != manifest_digest:
    raise SystemExit(
        f"workload manifest digest drifted: {actual_manifest_digest} != {manifest_digest}"
    )
receipt_parts = manifest_receipt_path.read_text(encoding="utf-8").strip().split()
if receipt_parts != [manifest_digest, "paper/workload_manifest.tsv"]:
    raise SystemExit(f"invalid workload manifest receipt: {receipt_parts}")

header, rows = read_tsv(manifest_path)
if header != expected_header:
    raise SystemExit(f"workload manifest schema mismatch: {header}")
if len(rows) != 29:
    raise SystemExit(f"expected 29 preregistered workload rows, found {len(rows)}")
workload_ids = [row["workload_id"] for row in rows]
if workload_ids != sorted(workload_ids) or len(workload_ids) != len(set(workload_ids)):
    raise SystemExit("workload IDs must be unique and stable-sorted")
if {row["claim_id"] for row in rows} != {f"C{index}" for index in range(1, 8)}:
    raise SystemExit("workload manifest does not cover C1-C7")
if not {row["role"] for row in rows}.issubset(allowed_roles):
    raise SystemExit("workload manifest contains an unsupported role")
if not {row["output_contract"] for row in rows}.issubset(allowed_contracts):
    raise SystemExit("workload manifest contains an unsupported output contract")
if any(row["preregistered"] != "1" for row in rows):
    raise SystemExit("all workload rows must be preregistered")

digest_cache: dict[Path, str] = {}
for row in rows:
    if any(not row[column] for column in expected_header):
        raise SystemExit(f"{row['workload_id']}: empty manifest field")
    try:
        start = int(row["query_start_nt"])
        end = int(row["query_end_nt"])
        length = int(row["query_length_nt"])
        pairs = int(row["required_pairs"])
        required_gpus = int(row["requires_gpu_count"])
        timeout = int(row["max_wall_seconds"])
        int(row["rule"])
    except ValueError as exc:
        raise SystemExit(f"{row['workload_id']}: invalid numeric field") from exc
    if start < 0 or end <= start or end - start != length:
        raise SystemExit(f"{row['workload_id']}: invalid query interval")
    if pairs < 0 or required_gpus < 0 or timeout <= 0:
        raise SystemExit(f"{row['workload_id']}: invalid run requirement")
    for path_key, digest_key in (
        ("query_path", "query_sha256"),
        ("target_path", "target_sha256"),
    ):
        input_path = resolve_manifest_path(row[path_key])
        if not input_path.is_file():
            raise SystemExit(f"{row['workload_id']}: missing input {input_path}")
        digest = digest_cache.setdefault(input_path, sha256(input_path))
        if digest != row[digest_key]:
            raise SystemExit(f"{row['workload_id']}: {path_key} digest mismatch")

generalization_core = [row for row in rows if row["role"] == "generalization_core"]
breadth = [row for row in rows if row["role"] == "breadth"]
supported = generalization_core + breadth
if len(generalization_core) != 9 or any(row["required_pairs"] != "3" for row in generalization_core):
    raise SystemExit("generalization core must contain nine three-pair rows")
if len(breadth) != 4 or any(row["required_pairs"] != "1" for row in breadth):
    raise SystemExit("generalization breadth must contain four one-pair rows")
if any(row["claim_id"] != "C2" for row in supported):
    raise SystemExit("supported generalization rows must map to C2")
if any(row["output_contract"] != "fast_topk_score_stability_nt" for row in supported):
    raise SystemExit("supported generalization rows must use one top-K contract")
if {row["preset_id"] for row in supported} != {"gasal2_short_topk_v1"}:
    raise SystemExit("supported generalization rows must use one frozen preset")
if any(row["adapter_id"] != "direct_tfo_contract" for row in supported):
    raise SystemExit("supported generalization rows must use the direct contract adapter")
identities = {row["query_id"] for row in supported}
if len(identities) < 4 or len(identities - {"H19"}) < 3:
    raise SystemExit("generalization identity coverage is insufficient")
if not {1024, 2048, 2812}.issubset({int(row["query_length_nt"]) for row in supported}):
    raise SystemExit("generalization length coverage is insufficient")
if not {"5p", "mid", "3p"}.issubset({row["fragment_position"] for row in supported}):
    raise SystemExit("generalization fragment-position coverage is insufficient")
generalization_targets = {row["target_id"] for row in supported}
for chromosome in ("chr11", "chr21", "chr22"):
    if not any(target.startswith(chromosome) for target in generalization_targets):
        raise SystemExit(f"generalization target coverage is missing {chromosome}")

negative_controls = [row for row in rows if row["role"] == "negative_control"]
if len(negative_controls) != 3:
    raise SystemExit("expected three full-length negative controls")
if {row["query_id"] for row in negative_controls} != {"MALAT1", "NEAT1", "KCNQ1OT1"}:
    raise SystemExit("full-length guard identities drifted")
if any(
    row["required_pairs"] != "0"
    or row["adapter_id"] != "preflight_guard"
    or row["output_contract"] != "preflight_guard_only"
    for row in negative_controls
):
    raise SystemExit("negative controls must remain preflight-only")

by_id = {row["workload_id"]: row for row in rows}
if by_id["c1_h19_chr21_chr22_fast_topk"]["required_pairs"] != "5":
    raise SystemExit("C1 core workload must retain five pairs")
if int(by_id["c1_h19_chr21_chr22_fast_topk"]["max_wall_seconds"]) < 2700:
    raise SystemExit("C1 timeout must cover the preregistered two-chromosome CPU authority")
for workload_id in ("c4_h19_chr21_two_slot", "c4_h19_chr22_two_slot"):
    if by_id[workload_id]["required_pairs"] != "5":
        raise SystemExit(f"{workload_id} must retain five pairs")
if by_id["c7_kcnq_max8_chr22"]["required_pairs"] != "3":
    raise SystemExit("C7 bounded max8 workload must retain three pairs")

environment = json.loads(environment_path.read_text(encoding="utf-8"))
if environment.get("schema_version") != 1:
    raise SystemExit("environment capture schema mismatch")
for field in (
    "captured_at_utc",
    "platform",
    "python",
    "cuda_visible_devices",
    "cpu_governors",
    "uname",
    "lscpu",
    "compiler",
    "nvcc",
    "nvidia_smi",
):
    if field not in environment:
        raise SystemExit(f"environment capture missing {field}")

dry_run = json.loads(dry_run_path.read_text(encoding="utf-8"))
if dry_run.get("schema_version") != 1:
    raise SystemExit("dry-run schema mismatch")
if dry_run.get("runtime_epoch") != 0 or dry_run.get("runtime_commit") != baseline:
    raise SystemExit("dry-run runtime freeze drifted")
if dry_run.get("seed") != seed:
    raise SystemExit("dry-run seed drifted")
if dry_run.get("workload_count") != 29 or dry_run.get("run_count") != 139:
    raise SystemExit("dry-run does not cover the complete preregistered manifest")
runs = dry_run.get("runs")
warmups = dry_run.get("warmups")
if not isinstance(runs, list) or len(runs) != 139:
    raise SystemExit("dry-run run list is incomplete")
if not isinstance(warmups, list) or len(warmups) != 52:
    raise SystemExit("dry-run warm-up list is incomplete")
run_ids = [str(run.get("run_id", "")) for run in runs]
if len(run_ids) != len(set(run_ids)) or any(not run_id for run_id in run_ids):
    raise SystemExit("dry-run contains duplicate or empty run IDs")
if any(run.get("pair_order") not in {"AB", "BA"} for run in runs):
    raise SystemExit("dry-run paired order is not reproducible")

harness = harness_py_path.read_text(encoding="utf-8")
for phrase in (
    "os.replace(temporary, path)",
    "config_digest_sha256",
    "config digest mismatch",
    "incomplete receipt",
    "duplicate run ID",
    "blocked_reason=insufficient_visible_gpus",
    "unavailable,NA,NA,NA,NA",
    "warmup_run_id",
    "/usr/bin/time",
    "FASIM_PAPER_HARNESS_TEST_MODE",
):
    if phrase not in harness:
        raise SystemExit(f"benchmark harness missing contract: {phrase}")
collector = collector_path.read_text(encoding="utf-8")
if "missing collector input" not in collector or "gpu_memory_sample" not in collector:
    raise SystemExit("paper run collector does not fail closed or report GPU memory")
tests = harness_test_path.read_text(encoding="utf-8")
for test_name in (
    "test_dry_run_expands_all_rows_and_is_seed_reproducible",
    "test_duplicate_resume_and_config_drift_fail_closed",
    "test_incomplete_receipt_cannot_resume",
    "test_warmup_has_a_separate_receipt",
    "test_collector_rejects_missing_required_files",
    "test_gpu_unavailable_reports_blocked_reason",
):
    if test_name not in tests:
        raise SystemExit(f"missing paper harness test: {test_name}")

if subprocess.run(
    ["git", "-C", str(root), "diff", "--quiet", f"{baseline}..HEAD", "--", "fasim"],
    check=False,
).returncode != 0:
    raise SystemExit("runtime code changed after the frozen paper commit")
if subprocess.run(
    ["git", "-C", str(root), "diff", "--quiet", "--", "fasim"],
    check=False,
).returncode != 0 or subprocess.run(
    ["git", "-C", str(root), "diff", "--cached", "--quiet", "--", "fasim"],
    check=False,
).returncode != 0:
    raise SystemExit("uncommitted runtime code changes violate the Phase 1 freeze")
if sha256(binary_path) != "613b24d9190b8b931661fce231ded6662d2b2b3e5772262310e069c15f191cc8":
    raise SystemExit("paper runtime binary digest drifted")

artifact_header, artifact_rows = read_tsv(artifacts_path)
inventory_paths = {row["artifact_path"] for row in artifact_rows}
for required_path in (
    "paper/benchmark_protocol.md",
    "paper/workload_manifest.tsv",
    "paper/workload_manifest.sha256",
):
    if required_path not in inventory_paths:
        raise SystemExit(f"Phase 1 artifact is not inventoried: {required_path}")
for row in artifact_rows:
    if row["artifact_path"] == "paper/benchmark_protocol.md":
        if row["sha256"] != sha256(protocol_path) or row["size_bytes"] != str(protocol_path.stat().st_size):
            raise SystemExit("protocol artifact inventory drifted")
    if row["artifact_path"] == "paper/workload_manifest.tsv":
        if row["sha256"] != manifest_digest or row["size_bytes"] != str(manifest_path.stat().st_size):
            raise SystemExit("manifest artifact inventory drifted")
    if row["artifact_path"] == "paper/workload_manifest.sha256":
        if row["sha256"] != sha256(manifest_receipt_path) or row["size_bytes"] != str(manifest_receipt_path.stat().st_size):
            raise SystemExit("manifest receipt artifact inventory drifted")

_, gap_rows = read_tsv(gaps_path)
gap_status = {row["gap_id"]: row["status"] for row in gap_rows}
for gap_id in (
    "generalization_preregistration",
    "generalization_target_diversity_gap",
):
    if gap_status.get(gap_id) != "resolved_phase1":
        raise SystemExit(f"Phase 1 gap is not resolved: {gap_id}")

_, claim_rows = read_tsv(claims_path)
claims = {row["claim_id"]: row for row in claim_rows}
for claim_id in ("C2", "C3"):
    gap = claims[claim_id]["gap"]
    if "manifest" not in gap.lower() or "frozen" not in gap.lower() or "run" not in gap.lower():
        raise SystemExit(f"{claim_id}: gap text does not separate manifest freeze from pending runs")

goal = goal_path.read_text(encoding="utf-8")
state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
expected_state = {
    "paper_runtime_epoch": "0",
    "paper_runtime_commit": baseline,
    "active_phase": "2",
    "phase_0_status": "pass",
    "phase_1_status": "pass",
    "last_completed_phase": "1",
    "last_decision": "paper_benchmark_protocol_and_manifest_frozen",
    "last_evidence_doc": "paper/benchmark_protocol.md",
    "last_test_command": "make check-fasim-gasal2-paper-phase1",
    "last_commit": "bench: preregister paper workloads and add digest-aware harness",
}
for key, expected in expected_state.items():
    if state.get(key) != expected:
        raise SystemExit(f"goal state mismatch for {key}: {state.get(key)!r} != {expected!r}")

makefile = makefile_path.read_text(encoding="utf-8")
if "check-fasim-gasal2-paper-phase1:" not in makefile:
    raise SystemExit("Makefile is missing the paper Phase 1 target")

print("Fasim GASAL2 paper Phase 1 OK")
PY
