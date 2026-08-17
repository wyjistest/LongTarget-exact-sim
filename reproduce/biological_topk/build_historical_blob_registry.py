#!/usr/bin/env python3
"""Rebuild the Phase 0 registry from execution-start Git blobs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXECUTION_START_HEAD = "2658a98fea8f34bd295892e6236607060e2f2803"
OUTPUT = ROOT / "paper/biological_topk/historical_blob_registry.tsv"

FIELDS = (
    "path",
    "frozen_at_commit",
    "git_blob_sha1",
    "blob_sha256",
    "size_bytes",
    "evidence_role",
    "live_path_mutable",
    "frozen_blob_mutable",
)

HISTORICAL_PATHS = (
    "Makefile",
    "README.md",
    "goal.md",
    "goal-final.md",
    "goal-bioinformatics.md",
    "goal-ssw.md",
    "paper/PAPER_PREP_STATUS.md",
    "paper/scope_and_claims.md",
    "paper/generalization_report.md",
    "paper/bioinformatics/README.md",
    "paper/bioinformatics/phase2_decision.md",
    "paper/bioinformatics/holdout_mismatch_details.tsv",
    "paper/bioinformatics/canonical_hybrid_v2_regression_decision.md",
    "paper/bioinformatics/canonical_hybrid_v2_holdout_decision.md",
    "paper/bioinformatics/canonical_hybrid_v2_performance_decision.md",
    "paper/bioinformatics/application_selection.json",
    "paper/ssw_cuda/PROGRAM_STATE.json",
    "paper/ssw_cuda/STATUS.md",
    "paper/ssw_cuda/final_decision.json",
    "paper/ssw_cuda/used_input_exclusion_registry.tsv",
    "paper/ssw_cuda/corpus_manifest.tsv",
    "scripts/compare_fasim_lite_offline_cluster_topk.py",
    "scripts/compare_fasim_segmented_contract.py",
    "scripts/fasim_tfo_archive.py",
    "reproduce/ssw_cuda/freeze_phase0.py",
    "fasim/fastsim.h",
    "fasim/Fasim-LongTarget.cpp",
)


class RegistryError(RuntimeError):
    pass


def git_bytes(*arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RegistryError(
            completed.stderr.decode("utf-8", errors="replace").strip()
            or f"git command failed: {' '.join(arguments)}"
        )
    return completed.stdout


def git_text(*arguments: str) -> str:
    return git_bytes(*arguments).decode("ascii").strip()


def evidence_role(path: str) -> str:
    if path.startswith("goal"):
        return "historical_protocol_state"
    if path.startswith("paper/ssw_cuda/"):
        return "exact_ssw_cuda_historical_boundary"
    if "canonical_hybrid_v2" in path:
        return "canonical_hybrid_v2_historical_decision"
    if path.startswith("paper/bioinformatics/"):
        return "bioinformatics_historical_evidence"
    if path.startswith("paper/"):
        return "historical_paper_claim_boundary"
    if path.startswith(("fasim/", "scripts/", "reproduce/")):
        return "historical_implementation_semantics"
    return "historical_repository_context"


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in HISTORICAL_PATHS:
        payload = git_bytes("show", f"{EXECUTION_START_HEAD}:{path}")
        rows.append(
            {
                "path": path,
                "frozen_at_commit": EXECUTION_START_HEAD,
                "git_blob_sha1": git_text("rev-parse", f"{EXECUTION_START_HEAD}:{path}"),
                "blob_sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "evidence_role": evidence_role(path),
                "live_path_mutable": 1,
                "frozen_blob_mutable": 0,
            }
        )
    return rows


def render() -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(build_rows())
    return output.getvalue().encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = render()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(payload)
    elif not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
        raise RegistryError("historical blob registry does not rebuild byte-for-byte")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegistryError as error:
        print(f"historical registry error: {error}", file=__import__("sys").stderr)
        raise SystemExit(1)
