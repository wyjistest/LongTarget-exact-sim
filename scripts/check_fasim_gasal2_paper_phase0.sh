#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOAL="$ROOT/goal-final.md"
README="$ROOT/paper/README.md"
SCOPE="$ROOT/paper/scope_and_claims.md"
CLAIMS="$ROOT/paper/claim_evidence.tsv"
ARTIFACTS="$ROOT/paper/artifact_inventory.tsv"
GAPS="$ROOT/paper/gap_register.tsv"
EPOCHS="$ROOT/paper/runtime_epoch_log.tsv"
FINAL_DECISION="$ROOT/docs/fasim_gasal2_long_query_final_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$GOAL" \
  "$README" \
  "$SCOPE" \
  "$CLAIMS" \
  "$ARTIFACTS" \
  "$GAPS" \
  "$EPOCHS" \
  "$FINAL_DECISION" \
  "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 0 dependency: $path" >&2
    exit 1
  fi
done

python3 - \
  "$ROOT" "$GOAL" "$README" "$SCOPE" "$CLAIMS" "$ARTIFACTS" \
  "$GAPS" "$EPOCHS" "$FINAL_DECISION" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path


root = Path(sys.argv[1])
goal_path = Path(sys.argv[2])
readme_path = Path(sys.argv[3])
scope_path = Path(sys.argv[4])
claims_path = Path(sys.argv[5])
artifacts_path = Path(sys.argv[6])
gaps_path = Path(sys.argv[7])
epochs_path = Path(sys.argv[8])
final_path = Path(sys.argv[9])
makefile_path = Path(sys.argv[10])

baseline = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
allowed_sources = {
    "reproduced_current_epoch",
    "reused_digest_verified",
    "committed_historical_artifact",
    "user_provided_external_result",
    "frozen_source_data",
    "unavailable",
}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        rows = list(reader)
    return reader.fieldnames, rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


goal_text = goal_path.read_text(encoding="utf-8")
state: dict[str, str] = {}
for raw in goal_text.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
if state.get("paper_baseline_commit") != baseline:
    raise SystemExit("paper baseline commit drifted")
if state.get("paper_runtime_epoch") != "0":
    raise SystemExit("paper runtime epoch must remain 0 in Phase 0")
if state.get("paper_runtime_commit") != baseline:
    raise SystemExit("paper runtime commit drifted")
active = state.get("active_phase", "")
if active != "complete" and (not active.isdigit() or int(active) < 1):
    raise SystemExit(f"paper Phase 0 is not complete: active_phase={active!r}")
if state.get("phase_0_status") != "pass":
    raise SystemExit("goal-final.md does not record phase_0_status = pass")
last_completed = state.get("last_completed_phase", "")
if not last_completed.isdigit() or int(last_completed) < 0:
    raise SystemExit("goal-final.md last_completed_phase is inconsistent")

if subprocess.run(
    ["git", "-C", str(root), "merge-base", "--is-ancestor", baseline, "HEAD"],
    check=False,
).returncode != 0:
    raise SystemExit("paper baseline commit is not an ancestor of HEAD")
if subprocess.run(
    ["git", "-C", str(root), "diff", "--quiet", f"{baseline}..HEAD", "--", "fasim"],
    check=False,
).returncode != 0:
    raise SystemExit("runtime code changed after the frozen paper commit")

readme = readme_path.read_text(encoding="utf-8")
for phrase in (
    "paper_runtime_epoch = 0",
    baseline,
    "goal-final.md",
    "paper/source_data",
    ".paper-artifacts/<data_freeze_id>",
):
    if phrase not in readme:
        raise SystemExit(f"paper README missing: {phrase}")

scope = scope_path.read_text(encoding="utf-8")
for claim_id in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
    if not re.search(rf"^## {claim_id}\b", scope, flags=re.MULTILINE):
        raise SystemExit(f"scope ledger missing section {claim_id}")
for phrase in (
    "short-query top-K",
    "long_query_architecture_no_go_with_complete_evidence",
    "full 121-segment candidate = not run",
    "full hg38 = not run",
    "one worker per GPU",
):
    if phrase not in scope:
        raise SystemExit(f"scope ledger missing boundary: {phrase}")
for forbidden in (
    "40x faster for LongTarget in general",
    "all lncRNAs are accelerated",
    "full-output GASAL2 replacement is validated",
    "full-length KCNQ1OT1 acceleration is validated",
):
    if forbidden in scope or forbidden in readme:
        raise SystemExit(f"unsupported universal paper claim: {forbidden}")

claim_header, claim_rows = read_tsv(claims_path)
expected_claim_header = [
    "claim_id",
    "claim_text_short",
    "contract",
    "workload_ids",
    "required_repeats",
    "correctness_gate",
    "primary_metric",
    "current_evidence_path",
    "current_source_class",
    "current_n",
    "current_value",
    "gap",
    "status",
]
phase5_claim_header = [
    "final_interval_or_range",
    "correctness_status",
    "source_data_filter",
    "allowed_manuscript_wording",
]
if claim_header != expected_claim_header and claim_header != expected_claim_header + phase5_claim_header:
    raise SystemExit(f"claim ledger schema mismatch: {claim_header}")
claim_ids = [row["claim_id"] for row in claim_rows]
if claim_ids != [f"C{index}" for index in range(1, 8)]:
    raise SystemExit(f"claim ledger must contain stable C1-C7 rows: {claim_ids}")
for row in claim_rows:
    for key in (
        "claim_text_short",
        "contract",
        "workload_ids",
        "required_repeats",
        "correctness_gate",
        "primary_metric",
        "gap",
        "status",
    ):
        if not row[key]:
            raise SystemExit(f"{row['claim_id']}: empty required claim field {key}")
    source = row["current_source_class"]
    if source not in allowed_sources:
        raise SystemExit(f"{row['claim_id']}: invalid source class {source!r}")
    if row["current_value"] not in ("", "NA"):
        if not row["current_evidence_path"] or source == "unavailable":
            raise SystemExit(f"{row['claim_id']}: current number lacks provenance")
    if row["current_n"] not in ("", "NA"):
        try:
            if int(row["current_n"]) < 0:
                raise ValueError
        except ValueError as exc:
            raise SystemExit(f"{row['claim_id']}: invalid current_n") from exc

artifact_header, artifact_rows = read_tsv(artifacts_path)
expected_artifact_header = [
    "artifact_id",
    "artifact_path",
    "artifact_kind",
    "exists",
    "size_bytes",
    "sha256",
    "producer_command",
    "runtime_commit",
    "input_digests",
    "config_digest",
    "created_at",
    "source_classification",
    "claim_ids",
    "notes",
]
if artifact_header != expected_artifact_header:
    raise SystemExit(f"artifact inventory schema mismatch: {artifact_header}")
artifact_ids = [row["artifact_id"] for row in artifact_rows]
if artifact_ids != sorted(artifact_ids) or len(artifact_ids) != len(set(artifact_ids)):
    raise SystemExit("artifact inventory must be uniquely stable-sorted by artifact_id")
if len(artifact_rows) < 14:
    raise SystemExit("artifact inventory is too small to cover the frozen evidence")
covered_claims: set[str] = set()
inventory_paths = {row["artifact_path"] for row in artifact_rows}
for row in artifact_rows:
    if row["source_classification"] not in allowed_sources:
        raise SystemExit(f"{row['artifact_id']}: invalid source classification")
    claims = {value for value in row["claim_ids"].split(",") if value}
    if not claims.issubset({f"C{index}" for index in range(1, 8)}):
        raise SystemExit(f"{row['artifact_id']}: invalid claim IDs")
    covered_claims.update(claims)
    relative = Path(row["artifact_path"])
    path = relative if relative.is_absolute() else root / relative
    if row["exists"] == "1":
        if not path.is_file():
            raise SystemExit(f"{row['artifact_id']}: inventoried file is missing: {path}")
        if row["size_bytes"] != str(path.stat().st_size):
            raise SystemExit(f"{row['artifact_id']}: size drift")
        if row["sha256"] != sha256(path):
            raise SystemExit(f"{row['artifact_id']}: sha256 drift")
    elif row["exists"] == "0":
        if path.exists():
            raise SystemExit(f"{row['artifact_id']}: marked unavailable but path exists")
        if row["source_classification"] != "unavailable":
            raise SystemExit(f"{row['artifact_id']}: missing path must be unavailable")
        if row["size_bytes"] != "NA" or row["sha256"] != "NA":
            raise SystemExit(f"{row['artifact_id']}: missing path uses fabricated metadata")
    else:
        raise SystemExit(f"{row['artifact_id']}: exists must be 0 or 1")
    runtime_commit = row["runtime_commit"]
    if runtime_commit != "NA" and not re.fullmatch(r"[0-9a-f]{40}", runtime_commit):
        raise SystemExit(f"{row['artifact_id']}: invalid runtime commit")
if covered_claims != {f"C{index}" for index in range(1, 8)}:
    raise SystemExit(f"artifact inventory does not cover all claims: {covered_claims}")
for row in claim_rows:
    evidence_path = row["current_evidence_path"]
    if evidence_path and evidence_path != "NA" and evidence_path not in inventory_paths:
        raise SystemExit(
            f"{row['claim_id']}: current evidence is missing from artifact inventory"
        )
for path in (
    "docs/fasim_gasal2_long_query_final_decision.md",
    "docs/fasim_gasal2_long_query_architecture_baseline.md",
    "docs/fasim_gasal2_workload_matrix.tsv",
    "docs/fasim_gasal2_short_query_generalization_panel.md",
    "docs/fasim_gasal2_top5_recommended_runtime.md",
    "docs/fasim_gasal2_two_slot_recommended_runtime_readiness.md",
    "docs/fasim_gasal2_segmented_archive_first.md",
):
    if path not in inventory_paths:
        raise SystemExit(f"required Phase 0 evidence is not inventoried: {path}")

gap_header, gap_rows = read_tsv(gaps_path)
expected_gap_header = [
    "gap_id",
    "category",
    "description",
    "affects_claims",
    "severity",
    "resolution_phase",
    "evidence_path",
    "status",
]
if gap_header != expected_gap_header:
    raise SystemExit(f"gap register schema mismatch: {gap_header}")
gap_ids = {row["gap_id"] for row in gap_rows}
required_gaps = {
    "core_repeat_gaps",
    "generalization_target_diversity_gap",
    "raw_artifact_availability",
    "input_fasta_provenance",
    "second_gpu_platform_availability",
    "citation_metadata_gaps",
    "container_reproduction_gaps",
}
if not required_gaps.issubset(gap_ids):
    raise SystemExit(f"gap register missing categories: {sorted(required_gaps - gap_ids)}")
for row in gap_rows:
    if not all(row[key] for key in expected_gap_header):
        raise SystemExit(f"{row['gap_id']}: incomplete gap record")

epoch_header, epoch_rows = read_tsv(epochs_path)
expected_epoch_header = [
    "paper_runtime_epoch",
    "runtime_commit",
    "frozen_at_utc",
    "change_class",
    "affected_workloads",
    "reason",
    "status",
]
if epoch_header != expected_epoch_header or len(epoch_rows) != 1:
    raise SystemExit("runtime epoch log must contain one epoch-0 row")
epoch = epoch_rows[0]
if (
    epoch["paper_runtime_epoch"] != "0"
    or epoch["runtime_commit"] != baseline
    or epoch["change_class"] != "runtime_freeze"
    or epoch["status"] != "active"
):
    raise SystemExit(f"runtime epoch row drifted: {epoch}")

final_decision = final_path.read_text(encoding="utf-8")
if "long_query_architecture_no_go_with_complete_evidence" not in final_decision:
    raise SystemExit("long-query final no-go evidence is missing")
if "full segmented KCNQ1OT1 x chr22 integrated candidate=not run" not in final_decision:
    raise SystemExit("full long-query not-run boundary is missing")
makefile = makefile_path.read_text(encoding="utf-8")
if "check-fasim-gasal2-paper-phase0:" not in makefile:
    raise SystemExit("Makefile is missing the paper Phase 0 target")

print("Fasim GASAL2 paper Phase 0 OK")
PY
