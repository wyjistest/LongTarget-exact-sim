#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_architecture_baseline.md"
GOAL="$ROOT/goal.md"
MAKEFILE="$ROOT/Makefile"
ARCHIVE_SUMMARY="${PHASE0_ARCHIVE_SUMMARY:-$ROOT/.tmp/check_fasim_gasal2_long_query_phase0_archive/summary.txt}"

python3 - "$ROOT" "$DOC" "$GOAL" "$MAKEFILE" "$ARCHIVE_SUMMARY" <<'PY'
from pathlib import Path
import sys


root = Path(sys.argv[1])
doc_path = Path(sys.argv[2])
goal_path = Path(sys.argv[3])
makefile_path = Path(sys.argv[4])
archive_summary_path = Path(sys.argv[5])

required_paths = [
    root / "scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh",
    root / "scripts/merge_fasim_segmented_tfosorted.py",
    root / "scripts/compare_fasim_lite_offline_cluster_topk.py",
    root / "scripts/compare_fasim_lite_full_equivalence.py",
    root / "scripts/compare_fasim_tfosorted_tfo_contract.py",
    root / "scripts/restore_fasim_tfosorted_column_archive_probe.py",
    root / "scripts/check_fasim_gasal2_archive_manifest.py",
    root / "scripts/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu.sh",
    root / "docs/fasim_gasal2_archive_first_output.md",
    root / "docs/fasim_gasal2_workload_matrix.tsv",
    root / "docs/fasim_gasal2_two_slot_recommended_runtime_readiness.md",
]
missing_paths = [str(path.relative_to(root)) for path in required_paths if not path.is_file()]
if missing_paths:
    raise SystemExit("missing Phase 0 dependency paths: " + ", ".join(missing_paths))

for path in (doc_path, goal_path, makefile_path, archive_summary_path):
    if not path.is_file():
        raise SystemExit(f"missing Phase 0 evidence file: {path}")

doc = " ".join(doc_path.read_text(encoding="utf-8").split())
doc_required = [
    "runtime_source_commit = 9949e258861ed3852c2c9cd363c1ecec3ee6fd89",
    "source = reproduced",
    "source = committed_artifact",
    "source = user_provided_external_result",
    "verified_in_current_checkout = 0",
    "Contract A: complete output",
    "Contract B: clustered top5",
    "Contract C: shifted-grid stability",
    "Contract D: archive-first restore",
    "top5_tfo_nt_score_equal = false",
    "full_missing_rows = 35",
    "full_extra_rows = 1115",
    "gasal2_requests = 2,189,813,851",
    "traceback_requests = 918,240,875",
    "exact_column_tasks = 46,562,736",
    "exact_column_cells = 232,813,680,000",
    "wall_sum_seconds = 8,687.413318",
    "artifact_bytes = 5,530,128,435",
    "peak_gpu_memory = NA (not captured)",
    "peak_host_rss = NA (not captured)",
    "testDNA.fa compound-header archive probe = fail",
    "runtime behavior change = 0",
    "fresh_build_binary_sha256 = 9e8241405d523b5a741dffb13c8e5923bbc4f0a8f38bef4179f68006ffedf27f",
    "not bit-for-bit binary reproducibility",
    "does not have one comparator that proves score-ranked, stability-ranked, and Nt-ranked results after the same clustering pass",
    "segmented_wall_sum_seconds = 5.395844",
    "not the CPU authority",
    "7d94fb9515b0fa63dbe8fb62e01bb50616760ce80eeef29ec9c3893af8040f4e",
    "7c44698a4ca63482ae0ae6c2c4aca4f2f13ff43ba3a5bbcf8543aed685bbdbb1",
    "e36fd5e349179420d36f7a2cca4503dbe1e82ad4d7eecb88afd421f0f23099ea",
    "f8883e1855017b7a28576770a8c8476a8eb1adbfcbef08d55c6dc74c49a86cc4",
    "ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f",
]
missing_doc = [phrase for phrase in doc_required if phrase not in doc]
if missing_doc:
    raise SystemExit("Phase 0 baseline doc missing phrases: " + ", ".join(missing_doc))

goal = goal_path.read_text(encoding="utf-8")
goal_state = {}
for raw_line in goal.splitlines():
    if " = " in raw_line:
        key, value = raw_line.split(" = ", 1)
        goal_state.setdefault(key, value)
try:
    active_phase = int(goal_state.get("active_phase", "-1"))
    last_completed_phase = int(goal_state.get("last_completed_phase", "-1"))
except ValueError as exc:
    raise SystemExit("goal.md Phase 0 status contains a non-integer phase") from exc
if (
    goal_state.get("phase_0_status") != "pass"
    or active_phase < 1
    or last_completed_phase < 0
):
    raise SystemExit("goal.md Phase 0 status is missing or has regressed")

makefile = makefile_path.read_text(encoding="utf-8")
make_required = [
    "check-fasim-gasal2-long-query-phase0:",
    "$(MAKE) check-fasim-gasal2-reproducible-setup",
    "$(MAKE) check-sample",
    "$(MAKE) check-fasim-tfo-archive-integrity-parser",
    "$(MAKE) check-fasim-gasal2-archive-manifest-parser",
    "$(MAKE) check-fasim-lite-full-equivalence",
    "$(MAKE) check-fasim-gasal2-top5-output-contract",
    "$(MAKE) check-fasim-gasal2-short-query-top5-tfo-contract",
    "$(MAKE) check-fasim-gasal2-archive-first-output",
    "scripts/check_fasim_gasal2_long_query_phase0.sh",
]
missing_make = [phrase for phrase in make_required if phrase not in makefile]
if missing_make:
    raise SystemExit("Phase 0 Make target missing phrases: " + ", ".join(missing_make))

summary = {}
for raw_line in archive_summary_path.read_text(encoding="utf-8").splitlines():
    if "=" not in raw_line:
        continue
    key, value = raw_line.split("=", 1)
    summary[key] = value

expected_summary = {
    "compare_mode": "byte",
    "archive_first_requested": "1",
    "archive_first_active": "1",
    "archive_first_decision": "active",
    "restored_equal": "1",
    "legacy_only_rows": "0",
    "archive_only_rows": "0",
    "archive_manifest_valid": "1",
    "archive_manifest_decision": "ready",
    "archive_magic": "FATFOC1",
    "archive_version": "2",
    "archive_terminator_present": "1",
    "query_fasta_sha256": "7d94fb9515b0fa63dbe8fb62e01bb50616760ce80eeef29ec9c3893af8040f4e",
    "target_fasta_sha256": "e36fd5e349179420d36f7a2cca4503dbe1e82ad4d7eecb88afd421f0f23099ea",
}
bad_summary = [
    f"{key}={summary.get(key)!r} (expected {value!r})"
    for key, value in expected_summary.items()
    if summary.get(key) != value
]
if bad_summary:
    raise SystemExit("Phase 0 archive smoke mismatch: " + ", ".join(bad_summary))

print("Fasim GASAL2 long-query Phase 0 baseline OK")
PY
