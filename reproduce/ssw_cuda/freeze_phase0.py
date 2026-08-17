#!/usr/bin/env python3
"""Build and validate the Phase 0 SSW-CUDA evidence freeze."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/ssw_cuda"
PHASE0_ARTIFACT_ROOT = ROOT / ".paper-artifacts/ssw-cuda-v1/phase0"
AUTHORITY_BINARY = PHASE0_ARTIFACT_ROOT / "fasim_longtarget_x86"
EXECUTION_START_HEAD = "9f87aace6d96cf8142e3816299f04defae5710e4"
EXECUTION_BRANCH = "gasal2-kcnq1ot1-focused-review"
REVIEWED_GOAL_SHA256 = "1d340e752d5e289dbda14d88c382bfd8f5c79eecb4c832fd524090c9fa4e613f"
PAIR_DIGEST_SCHEMA = "ssw-cuda-exclusion-pair-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

HISTORICAL_INVENTORY = PAPER / "historical_evidence_inventory.tsv"
HISTORICAL_RECEIPT = PAPER / "historical_evidence_receipt.json"
REGISTRY = PAPER / "used_input_exclusion_registry.tsv"
REGISTRY_CHECKSUM = PAPER / "used_input_exclusion_registry.sha256"
SOURCE_INVENTORY = PAPER / "source_inventory.tsv"
LICENSE_INVENTORY = PAPER / "license_inventory.tsv"
RUNTIME_EPOCHS = PAPER / "runtime_epochs.json"
CLAIM_LEDGER = PAPER / "claim_ledger.tsv"
PROGRAM_STATE = PAPER / "PROGRAM_STATE.json"
BASELINE_CHECK_RECEIPT = PAPER / "baseline_check_receipt.json"

HISTORICAL_FIELDS = (
    "path",
    "evidence_group",
    "size_bytes",
    "sha256",
    "git_blob_sha1",
)
SOURCE_FIELDS = (
    "path",
    "role",
    "source_commit",
    "size_bytes",
    "sha256",
    "git_blob_sha1",
)
REGISTRY_FIELDS = (
    "record_type",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "query_id",
    "target_id",
    "query_sha256",
    "target_sha256",
    "query_region",
    "target_region",
    "pair_digest",
    "source_receipt_path",
    "exclusion_reason",
)
LICENSE_FIELDS = (
    "component",
    "license_expression",
    "notice_path",
    "notice_sha256",
    "source_commit",
    "use_status",
    "notes",
)
CLAIM_FIELDS = (
    "claim_id",
    "status",
    "allowed_wording",
    "prohibited_wording",
    "evidence",
)


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def run(
    arguments: Sequence[str],
    *,
    cwd: Path = ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if check:
        require(
            completed.returncode == 0,
            completed.stderr.strip() or f"command failed: {' '.join(arguments)}",
        )
    return completed


def git(*arguments: str) -> str:
    return run(("git", *arguments)).stdout.strip()


def git_bytes(*arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    require(completed.returncode == 0,
            completed.stderr.decode("utf-8", errors="replace").strip() or
            f"git command failed: {' '.join(arguments)}")
    return completed.stdout


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def read_json(relative: str) -> object:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"missing JSON evidence: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(relative: str) -> list[dict[str, str]]:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"missing TSV evidence: {relative}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_ordinal(identifier: str, prefix: str) -> int:
    match = re.fullmatch(rf"{re.escape(prefix)}0*([1-9][0-9]*)", identifier)
    require(match is not None, f"invalid role-local identifier: {identifier}")
    return int(match.group(1))


def evidence_group(path: str) -> str:
    if "canonical_hybrid_v2" in path:
        return "canonical_hybrid_v2"
    if "phase2_traceback" in path:
        return "phase2_traceback_replay"
    if path.startswith("paper/bioinformatics/holdout") or "phase2" in path:
        return "phase2_holdout"
    if path.startswith("paper/bioinformatics/application") or "phase3" in path:
        return "phase3_application_pilot"
    if path.startswith("paper/source_data/") or path == "paper/workload_manifest.tsv":
        return "historical_paper"
    if path.startswith("reproduce/bioinformatics/application_inputs/"):
        return "phase3_application_inputs"
    if path.startswith("reproduce/bioinformatics/holdout_inputs/"):
        return "phase2_holdout_inputs"
    return "historical_support"


def historical_paths() -> list[str]:
    tracked = git("ls-files").splitlines()
    explicit = {
        "README.md",
        "goal.md",
        "goal-final.md",
        "goal-bioinformatics.md",
        "paper/PAPER_PREP_STATUS.md",
        "paper/workload_manifest.tsv",
        "config/gasal2_longtarget_contracts.json",
        "schemas/gasal2_longtarget_contracts.schema.json",
        "schemas/gasal2_longtarget_run_report.schema.json",
        "schemas/canonical_hybrid_v2_attempt_telemetry.schema.json",
        "patches/gasal2-fasim-bridge.patch",
    }
    prefixes = (
        "paper/bioinformatics/",
        "paper/source_data/",
        "reproduce/bioinformatics/",
    )
    script_prefixes = (
        "scripts/check_bioinformatics_",
        "scripts/freeze_bioinformatics_",
        "scripts/collect_bioinformatics_",
        "scripts/canonical_hybrid_v2_",
        "scripts/compare_fasim_",
        "scripts/replay_phase2_",
        "scripts/gasal2_longtarget.py",
    )
    test_markers = ("bioinformatics", "canonical_hybrid_v2", "gasal2_longtarget")
    selected = []
    for path in tracked:
        if path in explicit or path.startswith(prefixes) or path.startswith(script_prefixes):
            selected.append(path)
        elif path.startswith("tests/") and any(marker in path for marker in test_markers):
            selected.append(path)
    required = {
        "paper/bioinformatics/phase2_decision.md",
        "paper/bioinformatics/phase3_postpilot_decision.json",
        "paper/bioinformatics/application_pilot_receipt.json",
        "paper/bioinformatics/holdout_summary.json",
        "paper/bioinformatics/canonical_hybrid_v2_regression_receipt.json",
        "paper/bioinformatics/canonical_hybrid_v2_holdout_receipt.json",
        "paper/bioinformatics/canonical_hybrid_v2_performance_receipt.json",
    }
    require(required.issubset(selected), "historical evidence selection missed a required receipt")
    return sorted(set(selected))


def build_historical_inventory() -> list[dict[str, object]]:
    rows = []
    for relative in historical_paths():
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"unsafe historical evidence: {relative}")
        rows.append(
            {
                "path": relative,
                "evidence_group": evidence_group(relative),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "git_blob_sha1": git("hash-object", "--", relative),
            }
        )
    return rows


def source_paths() -> list[str]:
    # The Phase 0 authority inventory is an epoch snapshot, not a live glob.
    # Later SSW-CUDA phases add headers under fasim/, which must not expand it.
    paths = {
        "Makefile",
        "fasim/fastSim.h",
        "fasim/fastsim.h",
        "fasim/Fasim-LongTarget.cpp",
        "fasim/gasal2_align_bridge.h",
        "fasim/gasal2_traceback_certificate.h",
        "fasim/rules.h",
        "fasim/sim.h",
        "fasim/ssw.h",
        "fasim/ssw_cpp.cpp",
        "fasim/ssw_cpp.h",
        "fasim/sswNew.cpp",
        "fasim/stats.h",
        "fasim/gasal2_align_bridge_stub.cpp",
        "cuda/prealign_cuda_stub.cpp",
        "cuda/prealign_cuda.h",
    }
    return sorted(paths)


def source_role(relative: str) -> str:
    if relative == "Makefile":
        return "build_contract"
    if "ssw" in Path(relative).name.lower():
        return "modified_ssw_oracle"
    if relative.endswith("stub.cpp"):
        return "cpu_backend_stub"
    if relative.endswith(".h"):
        return "runtime_header"
    return "authority_call_chain"


def build_source_inventory() -> list[dict[str, object]]:
    rows = []
    for relative in source_paths():
        completed = subprocess.run(
            ["git", "show", f"{EXECUTION_START_HEAD}:{relative}"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        require(completed.returncode == 0, f"cannot read frozen CPU authority source: {relative}")
        payload = completed.stdout
        rows.append(
            {
                "path": relative,
                "role": source_role(relative),
                "source_commit": EXECUTION_START_HEAD,
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "git_blob_sha1": git("rev-parse", f"{EXECUTION_START_HEAD}:{relative}"),
            }
        )
    return rows


def canonical_pair_digest(fields: dict[str, str]) -> str:
    payload = {"schema": PAIR_DIGEST_SCHEMA, **fields}
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def build_registry() -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}

    def add_pair(
        *,
        query_namespace: str,
        query_ordinal: str | int,
        target_namespace: str,
        target_ordinal: str | int,
        query_id: str,
        target_id: str,
        query_sha256: str,
        target_sha256: str,
        query_region: str,
        target_region: str,
        source: str,
        reason: str,
    ) -> None:
        require(SHA256_RE.fullmatch(query_sha256) is not None, f"invalid query digest: {query_id}")
        require(SHA256_RE.fullmatch(target_sha256) is not None, f"invalid target digest: {target_id}")
        identity = {
            "query_ordinal_namespace": query_namespace,
            "query_source_ordinal": str(query_ordinal),
            "target_ordinal_namespace": target_namespace,
            "target_source_ordinal": str(target_ordinal),
            "query_id": query_id,
            "target_id": target_id,
            "query_sha256": query_sha256,
            "target_sha256": target_sha256,
            "query_region": query_region,
            "target_region": target_region,
        }
        digest = canonical_pair_digest(identity)
        if digest not in merged:
            merged[digest] = {
                "record_type": "pair",
                **identity,
                "pair_digest": digest,
                "source_receipt_path": source,
                "exclusion_reason": reason,
            }
            return
        row = merged[digest]
        sources = set(str(row["source_receipt_path"]).split(";"))
        reasons = set(str(row["exclusion_reason"]).split(";"))
        sources.add(source)
        reasons.add(reason)
        row["source_receipt_path"] = ";".join(sorted(sources))
        row["exclusion_reason"] = ";".join(sorted(reasons))

    def add_query_only(query_id: str, query_sha256: str, source: str, reason: str) -> None:
        require(SHA256_RE.fullmatch(query_sha256) is not None, f"invalid query-only digest: {query_id}")
        key = f"query:{query_sha256}"
        if key not in merged:
            merged[key] = {
                "record_type": "query_only",
                "query_ordinal_namespace": "historical_development",
                "query_source_ordinal": "NA",
                "target_ordinal_namespace": "NA",
                "target_source_ordinal": "NA",
                "query_id": query_id,
                "target_id": "NA",
                "query_sha256": query_sha256,
                "target_sha256": "NA",
                "query_region": "as_recorded",
                "target_region": "NA",
                "pair_digest": "NA",
                "source_receipt_path": source,
                "exclusion_reason": reason,
            }
            return
        row = merged[key]
        row["query_id"] = ";".join(sorted(set(str(row["query_id"]).split(";")) | {query_id}))

    for row in read_tsv("paper/workload_manifest.tsv"):
        add_pair(
            query_namespace="historical_workload_manifest",
            query_ordinal="NA",
            target_namespace="historical_workload_manifest",
            target_ordinal="NA",
            query_id=row["query_id"],
            target_id=row["target_id"],
            query_sha256=row["query_sha256"],
            target_sha256=row["target_sha256"],
            query_region=f"{row['query_start_nt']}:{row['query_end_nt']}",
            target_region=row["target_region"],
            source="paper/workload_manifest.tsv",
            reason="historical_development_or_paper_workload",
        )

    holdout_rows = read_tsv("paper/bioinformatics/holdout_manifest.tsv")
    for row in holdout_rows:
        reasons = ["phase2_correctness_holdout", "canonical_hybrid_v2_regression"]
        if row["workload_id"] == "hq01_ht01":
            reasons.append("phase2_fixed_pilot")
        if row["query_id"] in {"hq10", "hq11"} and row["target_id"] == "ht02":
            reasons.append("phase2_traceback_replay")
        for reason in reasons:
            add_pair(
                query_namespace="phase2_holdout_role_ordinal",
                query_ordinal=parse_ordinal(row["query_id"], "hq"),
                target_namespace="phase2_holdout_role_ordinal",
                target_ordinal=parse_ordinal(row["target_id"], "ht"),
                query_id=row["query_id"],
                target_id=row["target_id"],
                query_sha256=row["query_sequence_sha256"],
                target_sha256=row["target_sequence_sha256"],
                query_region="full",
                target_region="full",
                source=(
                    "paper/bioinformatics/holdout_summary.json"
                    if reason == "phase2_fixed_pilot"
                    else "paper/bioinformatics/holdout_manifest.tsv"
                ),
                reason=reason,
            )

    application_rows = read_tsv("paper/bioinformatics/application_manifest.tsv")
    application = {row["record_id"]: row for row in application_rows}
    require(len(application) == len(application_rows) == 718, "application manifest identity drift")

    def add_application_pair(query_id: str, target_id: str, source: str, reason: str) -> None:
        query = application[query_id]
        target = application[target_id]
        require(query["record_role"] == "query" and target["record_role"] == "target", "application role drift")
        add_pair(
            query_namespace="phase3_application_role_ordinal",
            query_ordinal=parse_ordinal(query_id, "aq"),
            target_namespace="phase3_application_role_ordinal",
            target_ordinal=parse_ordinal(target_id, "at"),
            query_id=query_id,
            target_id=target_id,
            query_sha256=query["sequence_sha256"],
            target_sha256=target["sequence_sha256"],
            query_region="full",
            target_region="full",
            source=source,
            reason=reason,
        )

    add_application_pair(
        "aq001",
        "at0001",
        "paper/bioinformatics/application_pilot_receipt.json",
        "phase3_v1_fixed_pilot",
    )
    for relative, reason in (
        (
            "paper/bioinformatics/canonical_hybrid_v2_holdout_workloads.tsv",
            "canonical_hybrid_v2_fresh_holdout",
        ),
        (
            "paper/bioinformatics/canonical_hybrid_v2_performance_workloads.tsv",
            "canonical_hybrid_v2_performance_pilot",
        ),
    ):
        for row in read_tsv(relative):
            require(parse_ordinal(row["query_id"], "aq") == int(row["query_source_ordinal"]), "query ordinal drift")
            require(parse_ordinal(row["target_id"], "at") == int(row["target_source_ordinal"]), "target ordinal drift")
            add_application_pair(row["query_id"], row["target_id"], relative, reason)

    for row in read_tsv("paper/bioinformatics/development_query_exclusions.tsv"):
        if row["exclusion_type"] == "sequence_sha256":
            add_query_only(
                row["reason"].split()[0],
                row["value"],
                "paper/bioinformatics/development_query_exclusions.tsv",
                "historical_development_query",
            )

    rows = list(merged.values())
    rows.sort(
        key=lambda row: (
            str(row["record_type"]),
            str(row["query_sha256"]),
            str(row["target_sha256"]),
            str(row["pair_digest"]),
        )
    )
    return rows


def build_license_inventory() -> list[dict[str, object]]:
    gasal_root = ROOT / ".tmp/GASAL2"
    gasal_license = gasal_root / "LICENSE"
    require(gasal_license.is_file() and not gasal_license.is_symlink(), "GASAL2 license is unavailable")
    gasal_commit = run(("git", "rev-parse", "HEAD"), cwd=gasal_root).stdout.strip()
    project_license = git_bytes("show", f"{EXECUTION_START_HEAD}:LICENSE")
    ssw_notice = git_bytes("show", f"{EXECUTION_START_HEAD}:fasim/sswNew.cpp")
    return [
        {
            "component": "LongTarget-exact-sim",
            "license_expression": "AGPL-3.0-or-later",
            "notice_path": "LICENSE",
            "notice_sha256": sha256_bytes(project_license),
            "source_commit": EXECUTION_START_HEAD,
            "use_status": "project_license",
            "notes": "Repository-level license declared by README and LICENSE.",
        },
        {
            "component": "Complete Striped Smith-Waterman core",
            "license_expression": "MIT AND BSD-2-Clause",
            "notice_path": "fasim/sswNew.cpp",
            "notice_sha256": sha256_bytes(ssw_notice),
            "source_commit": EXECUTION_START_HEAD,
            "use_status": "embedded_authority_source",
            "notes": "Both notices are embedded at the start of the modified SSW source.",
        },
        {
            "component": "GASAL2",
            "license_expression": "Apache-2.0",
            "notice_path": ".tmp/GASAL2/LICENSE",
            "notice_sha256": sha256_file(gasal_license),
            "source_commit": gasal_commit,
            "use_status": "historical_backend_reference",
            "notes": "Ignored pinned checkout patched by patches/gasal2-fasim-bridge.patch; not the new authority.",
        },
    ]


def cpu_metadata() -> dict[str, object]:
    cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    first: dict[str, str] = {}
    for line in cpuinfo.splitlines():
        if not line.strip():
            break
        if ":" in line:
            key, value = line.split(":", 1)
            first[key.strip()] = value.strip()
    return {
        "logical_cpu_count": os.cpu_count(),
        "model_name": first.get("model name", "unknown"),
        "microcode": first.get("microcode", "unknown"),
        "flags": first.get("flags", "").split(),
    }


def gpu_metadata() -> dict[str, object]:
    query = "index,name,uuid,compute_cap,memory.total,driver_version"
    completed = run(
        ("nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"),
        check=False,
    )
    if completed.returncode != 0:
        return {"status": "not_available", "error": completed.stderr.strip()}
    devices = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        require(len(fields) == 6, "unexpected nvidia-smi output")
        devices.append(
            {
                "index": int(fields[0]),
                "name": fields[1],
                "uuid": fields[2],
                "compute_capability": fields[3],
                "memory_total_mib": int(fields[4]),
                "driver_version": fields[5],
            }
        )
    return {"status": "available", "devices": devices}


def toolchain_metadata() -> dict[str, object]:
    compiler = shutil.which("g++")
    require(compiler is not None, "g++ is unavailable")
    compiler_path = Path(compiler).resolve()
    nvcc = Path("/usr/local/cuda/bin/nvcc")
    nvcc_result = run((str(nvcc), "--version"), check=False) if nvcc.exists() else None
    return {
        "compiler_path": str(compiler_path),
        "compiler_sha256": sha256_file(compiler_path),
        "compiler_version": run((compiler, "--version")).stdout.splitlines()[0],
        "make_version": run(("make", "--version")).stdout.splitlines()[0],
        "nvcc_path": str(nvcc) if nvcc.exists() else "not_available",
        "nvcc_version": nvcc_result.stdout.strip() if nvcc_result and nvcc_result.returncode == 0 else "not_available",
        "build_command": "make build-fasim FASIM_TARGET=.paper-artifacts/ssw-cuda-v1/phase0/fasim_longtarget_x86",
        "effective_cxx": "g++",
        "effective_flags": "-O3 -std=c++11 -pthread -msse2",
    }


def historical_summary() -> dict[str, object]:
    phase2 = read_json("paper/bioinformatics/holdout_summary.json")
    phase3 = read_json("paper/bioinformatics/phase3_postpilot_decision.json")
    regression = read_json("paper/bioinformatics/canonical_hybrid_v2_regression_receipt.json")
    holdout = read_json("paper/bioinformatics/canonical_hybrid_v2_holdout_receipt.json")
    performance = read_json("paper/bioinformatics/canonical_hybrid_v2_performance_receipt.json")
    assert isinstance(phase2, dict) and isinstance(phase3, dict)
    assert isinstance(regression, dict) and isinstance(holdout, dict) and isinstance(performance, dict)
    require(phase2["decision"] == "verified_only_contract", "Phase 2 decision drift")
    require(phase2["attempt_counts"]["represented"] == 36, "Phase 2 attempt count drift")
    require(phase2["attempt_counts"]["scientific_mismatch"] == 2, "Phase 2 mismatch count drift")
    require(phase3["selected_decision"] == "stop_after_pilot_futility", "Phase 3 decision drift")
    require(phase3["b3_status"] == "no_go" and not phase3["formal_execution_started"], "Phase 3 B3 drift")
    require(regression["all_three_clustered_top5_equal"] == 36, "v2 regression Top-5 drift")
    require(regression["full_output_equal"] == 35, "v2 regression full-output drift")
    require(holdout["all_three_clustered_top5_equal"] == 60, "v2 holdout drift")
    require(performance["all_three_clustered_top5_equal"] == 18, "v2 performance correctness drift")
    require(performance["b3_v2_status"] == "no_go", "v2 B3 drift")
    require(performance["rescue_track_status"] == "closed_performance_no_go", "v2 rescue status drift")
    require(abs(performance["primary_aggregate_speedup"] - 0.25759196676394047) < 1e-15, "v2 speedup drift")
    require(abs(performance["hybrid_slowdown_vs_authority"] - 3.8821086408972096) < 1e-15, "v2 slowdown drift")
    return {
        "phase2": {
            "decision": phase2["decision"],
            "formal_attempts": phase2["attempt_counts"]["represented"],
            "formal_workloads": phase2["workload_count"],
            "scientific_mismatches": phase2["attempt_counts"]["scientific_mismatch"],
            "technical_failures": phase2["attempt_counts"]["technical_failure"],
        },
        "phase3_v1": {
            "decision": phase3["selected_decision"],
            "b3_status": phase3["b3_status"],
            "formal_execution_started": phase3["formal_execution_started"],
        },
        "canonical_hybrid_v2": {
            "regression_top5_equal": regression["all_three_clustered_top5_equal"],
            "regression_full_output_equal": regression["full_output_equal"],
            "fresh_holdout_equal": holdout["all_three_clustered_top5_equal"],
            "performance_correct": performance["all_three_clustered_top5_equal"],
            "primary_speedup": performance["primary_aggregate_speedup"],
            "slowdown_vs_authority": performance["hybrid_slowdown_vs_authority"],
            "b3_status": performance["b3_v2_status"],
            "track": "closed",
        },
    }


def registry_statistics(rows: list[dict[str, object]]) -> dict[str, object]:
    reasons: Counter[str] = Counter()
    for row in rows:
        reasons.update(str(row["exclusion_reason"]).split(";"))
    return {
        "row_count": len(rows),
        "pair_count": sum(row["record_type"] == "pair" for row in rows),
        "query_only_count": sum(row["record_type"] == "query_only" for row in rows),
        "unique_query_digests": len({row["query_sha256"] for row in rows if row["query_sha256"] != "NA"}),
        "unique_target_digests": len({row["target_sha256"] for row in rows if row["target_sha256"] != "NA"}),
        "reason_row_counts": dict(sorted(reasons.items())),
    }


def validate_baseline_check_receipt() -> dict[str, object]:
    require(
        BASELINE_CHECK_RECEIPT.is_file() and not BASELINE_CHECK_RECEIPT.is_symlink(),
        "missing or unsafe baseline check receipt",
    )
    receipt = json.loads(BASELINE_CHECK_RECEIPT.read_text(encoding="utf-8"))
    require(receipt["schema_version"] == 1 and receipt["status"] == "pass", "baseline check status drift")
    require(receipt["execution_start_head"] == EXECUTION_START_HEAD, "baseline check commit drift")
    expected = {
        "phase2",
        "phase3_pilot_clean_checkout",
        "canonical_hybrid_v2_runtime",
        "canonical_hybrid_v2_regression",
        "canonical_hybrid_v2_holdout",
        "canonical_hybrid_v2_performance",
    }
    checks = receipt["checks"]
    require({check["check_id"] for check in checks} == expected, "baseline check inventory drift")
    require(len(checks) == len(expected), "duplicate baseline check ID")
    for check in checks:
        require(check["exit_code"] == 0, f"baseline check did not pass: {check['check_id']}")
        path = ROOT / check["log_path"]
        require(path.is_file() and not path.is_symlink(), f"baseline check log missing: {path}")
        require(sha256_file(path) == check["log_sha256"], f"baseline check log drift: {path}")
        require(check["required_marker"] in path.read_text(encoding="utf-8"), f"baseline marker missing: {path}")
    phase3 = next(check for check in checks if check["check_id"] == "phase3_pilot_clean_checkout")
    require(phase3["clean_checkout"] is True, "Phase 3 clean-checkout evidence missing")
    return {
        "path": str(BASELINE_CHECK_RECEIPT.relative_to(ROOT)),
        "sha256": sha256_file(BASELINE_CHECK_RECEIPT),
        "status": receipt["status"],
        "check_ids": sorted(expected),
        "phase3_clean_checkout": True,
    }


def claim_rows() -> list[dict[str, str]]:
    return [
        {
            "claim_id": "HIST_GPU_TRACEBACK_V1",
            "status": "verified_only_contract",
            "allowed_wording": "The v1 GPU traceback path requires verified comparison or CPU authority.",
            "prohibited_wording": "GPU-only v1 is contract-safe.",
            "evidence": "paper/bioinformatics/phase2_decision.md",
        },
        {
            "claim_id": "HIST_PHASE3_V1_B3",
            "status": "no_go",
            "allowed_wording": "Sequential verified-v1 failed the prospective B3 feasibility gate.",
            "prohibited_wording": "Sequential verification provides safe acceleration.",
            "evidence": "paper/bioinformatics/phase3_postpilot_decision.json",
        },
        {
            "claim_id": "HIST_CANONICAL_HYBRID_V2_CORRECTNESS",
            "status": "pass",
            "allowed_wording": "Canonical-hybrid-v2 passed its frozen clustered Top-5 contract holdout.",
            "prohibited_wording": "Canonical-hybrid-v2 is a full-output replacement.",
            "evidence": "paper/bioinformatics/canonical_hybrid_v2_holdout_receipt.json",
        },
        {
            "claim_id": "HIST_CANONICAL_HYBRID_V2_PERFORMANCE",
            "status": "no_go_closed",
            "allowed_wording": "Canonical-hybrid-v2 was 3.882109x slower than authority on the fixed pilot.",
            "prohibited_wording": "Canonical-hybrid-v2 provides safe acceleration.",
            "evidence": "paper/bioinformatics/canonical_hybrid_v2_performance_receipt.json",
        },
        {
            "claim_id": "SSW_CUDA_L1_L7",
            "status": "pending",
            "allowed_wording": "No new exact SSW-CUDA correctness claim is currently established.",
            "prohibited_wording": "The new SSW-CUDA backend is exact or safe.",
            "evidence": "NONE",
        },
        {
            "claim_id": "SSW_CUDA_L8",
            "status": "diagnostic_only",
            "allowed_wording": "Full-output equality is recorded only as a diagnostic.",
            "prohibited_wording": "Full-output exact replacement.",
            "evidence": "goal-ssw.md",
        },
        {
            "claim_id": "SSW_CUDA_B3",
            "status": "pending_amdahl",
            "allowed_wording": "B3 feasibility awaits the preregistered CPU Amdahl profile.",
            "prohibited_wording": "Bioinformatics widening is open or achieved.",
            "evidence": "NONE",
        },
    ]


def build_outputs(phase0_status: str, frozen_utc: str) -> dict[Path, bytes]:
    require(phase0_status in {"in_progress", "pass"}, "invalid Phase 0 status")
    require(git("rev-parse", "HEAD") == EXECUTION_START_HEAD, "Phase 0 write must run at the frozen start HEAD")
    require(git("branch", "--show-current") == EXECUTION_BRANCH, "execution branch drift")
    require(sha256_file(ROOT / "goal.md") == "8489d7a4e37c9a2d4bdee78fcee40158230c513bfc6adcea9993abd7b8c71509", "goal.md drift")
    require(sha256_file(ROOT / "goal-ssw.md") != REVIEWED_GOAL_SHA256, "goal-ssw state was not advanced to in_progress")
    require(AUTHORITY_BINARY.is_file(), "Phase 0 authority binary has not been built")

    historical_rows = build_historical_inventory()
    historical_payload = tsv_bytes(HISTORICAL_FIELDS, historical_rows)
    source_rows = build_source_inventory()
    source_payload = tsv_bytes(SOURCE_FIELDS, source_rows)
    registry_rows = build_registry()
    registry_payload = tsv_bytes(REGISTRY_FIELDS, registry_rows)
    license_payload = tsv_bytes(LICENSE_FIELDS, build_license_inventory())
    claim_payload = tsv_bytes(CLAIM_FIELDS, claim_rows())

    history = historical_summary()
    source_sha = sha256_bytes(source_payload)
    registry_sha = sha256_bytes(registry_payload)
    inventory_sha = sha256_bytes(historical_payload)
    binary_sha = sha256_file(AUTHORITY_BINARY)
    toolchain = toolchain_metadata()
    cpu = cpu_metadata()
    gpu = gpu_metadata()
    goals = {
        name: sha256_file(ROOT / name)
        for name in ("goal.md", "goal-final.md", "goal-bioinformatics.md")
    }
    receipt = {
        "schema_version": 1,
        "freeze_id": f"ssw-cuda-phase0-{EXECUTION_START_HEAD[:12]}",
        "frozen_utc": frozen_utc,
        "phase0_status": phase0_status,
        "execution_start": {
            "head": EXECUTION_START_HEAD,
            "branch": EXECUTION_BRANCH,
            "ahead_remote": 20,
            "behind_remote": 0,
            "initial_nonignored_worktree": ["?? goal-ssw.md"],
        },
        "historical_summary": history,
        "baseline_checks": validate_baseline_check_receipt(),
        "historical_evidence_inventory": {
            "path": str(HISTORICAL_INVENTORY.relative_to(ROOT)),
            "rows": len(historical_rows),
            "sha256": inventory_sha,
        },
        "used_input_exclusion_registry": {
            "path": str(REGISTRY.relative_to(ROOT)),
            "sha256": registry_sha,
            "pair_digest_schema": PAIR_DIGEST_SCHEMA,
            **registry_statistics(registry_rows),
        },
        "cpu_authority": {
            "epoch": 2,
            "source_commit": EXECUTION_START_HEAD,
            "source_inventory_path": str(SOURCE_INVENTORY.relative_to(ROOT)),
            "source_inventory_sha256": source_sha,
            "binary_path": str(AUTHORITY_BINARY.relative_to(ROOT)),
            "binary_sha256": binary_sha,
            "binary_size_bytes": AUTHORITY_BINARY.stat().st_size,
            "historical_v2_authority_binary_sha256_equal": binary_sha
            == "75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e",
            "toolchain": toolchain,
            "host": {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "kernel": platform.release(),
                "machine": platform.machine(),
                "cpu": cpu,
                "gpu": gpu,
            },
        },
        "program_epoch": {"ssw_cuda_program_epoch": 1, "runtime_commit": None},
        "historical_goal_sha256": goals,
        "l8_contract_status": "diagnostic_only",
        "bioinformatics_b3_track": "pending_amdahl",
        "engineering_track": "active",
    }
    runtime_epochs = {
        "schema_version": 1,
        "ssw_cpu_oracle_epoch": 2,
        "ssw_cuda_program_epoch": 1,
        "execution_start_head": EXECUTION_START_HEAD,
        "cpu_oracle": receipt["cpu_authority"],
        "historical_canonical_hybrid_v2": {
            "runtime_epoch": 1,
            "runtime_commit": "17525a6d02e5c8d11a2359ae540e117dc08c8f99",
            "status": "closed_performance_no_go",
        },
        "ssw_cuda_runtime": {"status": "not_implemented", "commit": None},
    }
    program_state = {
        "schema_version": 1,
        "active_phase": 1 if phase0_status == "pass" else 0,
        "phase_status": {str(index): (phase0_status if index == 0 else "pending") for index in range(14)},
        "execution_start_head": EXECUTION_START_HEAD,
        "execution_branch": EXECUTION_BRANCH,
        "ssw_cpu_oracle_epoch": 2,
        "ssw_cuda_program_epoch": 1,
        "bioinformatics_b3_track": "pending_amdahl",
        "engineering_track": "active",
        "l8_contract_status": "diagnostic_only",
        "last_decision": "phase0_evidence_frozen" if phase0_status == "pass" else "phase0_evidence_import_in_progress",
        "last_evidence": str(HISTORICAL_RECEIPT.relative_to(ROOT)),
    }
    return {
        HISTORICAL_INVENTORY: historical_payload,
        HISTORICAL_RECEIPT: json_bytes(receipt),
        REGISTRY: registry_payload,
        REGISTRY_CHECKSUM: f"{registry_sha}  {REGISTRY.name}\n".encode("ascii"),
        SOURCE_INVENTORY: source_payload,
        LICENSE_INVENTORY: license_payload,
        RUNTIME_EPOCHS: json_bytes(runtime_epochs),
        CLAIM_LEDGER: claim_payload,
        PROGRAM_STATE: json_bytes(program_state),
    }


def write_outputs(outputs: dict[Path, bytes]) -> None:
    PAPER.mkdir(parents=True, exist_ok=True)
    for path, payload in outputs.items():
        path.write_bytes(payload)


def check_outputs() -> None:
    for path in (
        HISTORICAL_INVENTORY,
        HISTORICAL_RECEIPT,
        REGISTRY,
        REGISTRY_CHECKSUM,
        SOURCE_INVENTORY,
        LICENSE_INVENTORY,
        RUNTIME_EPOCHS,
        CLAIM_LEDGER,
        PROGRAM_STATE,
        BASELINE_CHECK_RECEIPT,
    ):
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 0 output: {path}")

    receipt = json.loads(HISTORICAL_RECEIPT.read_text(encoding="utf-8"))
    inventory_payload = tsv_bytes(HISTORICAL_FIELDS, build_historical_inventory())
    registry_payload = tsv_bytes(REGISTRY_FIELDS, build_registry())
    source_payload = tsv_bytes(SOURCE_FIELDS, build_source_inventory())
    license_payload = tsv_bytes(LICENSE_FIELDS, build_license_inventory())
    require(HISTORICAL_INVENTORY.read_bytes() == inventory_payload, "historical inventory is not reproducible")
    require(REGISTRY.read_bytes() == registry_payload, "used-input registry is not reproducible")
    require(SOURCE_INVENTORY.read_bytes() == source_payload, "source inventory is not reproducible")
    require(LICENSE_INVENTORY.read_bytes() == license_payload, "license inventory is not reproducible")
    expected_claims = {row["claim_id"]: row for row in claim_rows()}
    observed_claim_rows = read_tsv(str(CLAIM_LEDGER.relative_to(ROOT)))
    require(len(observed_claim_rows) == len({row["claim_id"] for row in observed_claim_rows}),
            "claim ledger contains duplicate IDs")
    observed_claims = {row["claim_id"]: row for row in observed_claim_rows}
    for claim_id in (
        "HIST_GPU_TRACEBACK_V1",
        "HIST_PHASE3_V1_B3",
        "HIST_CANONICAL_HYBRID_V2_CORRECTNESS",
        "HIST_CANONICAL_HYBRID_V2_PERFORMANCE",
        "SSW_CUDA_L8",
    ):
        require(observed_claims.get(claim_id) == expected_claims[claim_id],
                f"immutable Phase 0 claim drift: {claim_id}")
    require(observed_claims.get("SSW_CUDA_B3", {}).get("status") in
            {"pending_amdahl", "closed_amdahl"},
            "invalid versioned B3 claim state")
    require(receipt["historical_summary"] == historical_summary(), "historical numeric summary drift")
    require(receipt["baseline_checks"] == validate_baseline_check_receipt(), "baseline check binding drift")
    require(receipt["historical_evidence_inventory"]["sha256"] == sha256_bytes(inventory_payload), "inventory binding drift")
    require(receipt["used_input_exclusion_registry"]["sha256"] == sha256_bytes(registry_payload), "registry binding drift")
    require(receipt["cpu_authority"]["source_inventory_sha256"] == sha256_bytes(source_payload), "source binding drift")
    require(receipt["cpu_authority"]["binary_sha256"] == sha256_file(AUTHORITY_BINARY), "authority binary drift")
    require(receipt["cpu_authority"]["historical_v2_authority_binary_sha256_equal"], "authority binary epoch mismatch")
    require(
        REGISTRY_CHECKSUM.read_text(encoding="ascii")
        == f"{sha256_bytes(registry_payload)}  {REGISTRY.name}\n",
        "registry checksum file drift",
    )
    state = json.loads(PROGRAM_STATE.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME_EPOCHS.read_text(encoding="utf-8"))
    require(state["l8_contract_status"] == "diagnostic_only", "L8 boundary drift")
    require(state["ssw_cpu_oracle_epoch"] == 2 and state["ssw_cuda_program_epoch"] == 1, "epoch drift")
    require(runtime["cpu_oracle"]["binary_sha256"] == receipt["cpu_authority"]["binary_sha256"], "runtime binary binding drift")
    require(runtime["historical_canonical_hybrid_v2"]["status"] == "closed_performance_no_go", "historical v2 runtime status drift")
    require(git("merge-base", "--is-ancestor", EXECUTION_START_HEAD, "HEAD") == "", "start HEAD is not an ancestor")
    require(sha256_file(ROOT / "goal.md") == receipt["historical_goal_sha256"]["goal.md"], "goal.md was overwritten")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--phase0-status", choices=("in_progress", "pass"), default="in_progress")
    parser.add_argument("--frozen-utc")
    args = parser.parse_args()
    if args.write:
        frozen_utc = args.frozen_utc or datetime.now(timezone.utc).isoformat()
        write_outputs(build_outputs(args.phase0_status, frozen_utc))
    else:
        check_outputs()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FreezeError as error:
        print(f"phase0 freeze error: {error}", file=sys.stderr)
        raise SystemExit(1)
