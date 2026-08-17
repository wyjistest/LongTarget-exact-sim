#!/usr/bin/env python3
"""Produce candidate-site reference artifacts with the frozen CPU Fasim binary."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gasal2_candidate_sites as candidate_sites  # noqa: E402
import gasal2_longtarget as legacy  # noqa: E402


AUTHORITY_BINARY = (
    ROOT
    / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86"
)
AUTHORITY_SHA256 = "75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e"


class CpuReferenceError(RuntimeError):
    pass


def receipt_mapping(receipt: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "receipt_kind": "biological_topk_input_receipt_v1",
        "workload_id": receipt.workload_id,
        "arm": receipt.arm,
        "evidence_role": receipt.evidence_role,
        "technical_success": receipt.technical_success,
        "output_valid": receipt.output_valid,
        "output_sha256": receipt.output_sha256,
        "query_fasta": str(receipt.query_fasta),
        "query_fasta_interval": list(receipt.query_fasta_interval),
        "target_fasta": str(receipt.target_fasta),
        "target_fasta_interval": list(receipt.target_fasta_interval),
        "target_region_start0": receipt.target_region_start0,
        "chromosome_or_target_id": receipt.chromosome_or_target_id,
        "input_identity": dict(receipt.input_identity),
    }


def identity_from_args(args: argparse.Namespace) -> candidate_sites.ProductIdentity:
    return candidate_sites.ProductIdentity(
        workload_id=args.workload_id,
        query_ordinal_namespace=args.query_ordinal_namespace,
        query_source_ordinal=args.query_source_ordinal,
        target_ordinal_namespace=args.target_ordinal_namespace,
        target_source_ordinal=args.target_source_ordinal,
        assembly=args.assembly,
        target_coordinate_namespace=args.target_coordinate_namespace,
        query_extraction_recipe_id=args.query_extraction_recipe_id,
        target_extraction_recipe_id=args.target_extraction_recipe_id,
        target_region_start0=args.target_region_start0,
    )


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if not args.binary.is_file() or legacy.sha256(args.binary) != AUTHORITY_SHA256:
        raise CpuReferenceError("CPU authority binary is missing or has drifted")
    if args.output.exists() or args.report.exists():
        raise CpuReferenceError("CPU reference output/report collision")
    query = candidate_sites.read_single_fasta(args.query, "query")
    target = candidate_sites.read_single_fasta(args.target, "target")
    if len(query.sequence) > legacy.MAX_GPU_QUERY_LENGTH:
        raise CpuReferenceError("query is outside the shared short-query envelope")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.partial.", dir=args.output.parent)
    )
    native = temporary / "native"
    native.mkdir()
    started = time.perf_counter()
    report: dict[str, Any] = {
        "schema_version": 1,
        "execution_mode": "cpu-reference-offline-arm",
        "scientific_contract": candidate_sites.SCIENTIFIC_CONTRACT,
        "output_schema": candidate_sites.OUTPUT_SCHEMA,
        "software_epoch": candidate_sites.SOFTWARE_EPOCH,
        "workload_id": args.workload_id,
        "status": "running",
        "binary_sha256": AUTHORITY_SHA256,
        "complete_cpu_authority_executed": True,
        "errors": [],
    }
    try:
        environment, explicit = legacy.sanitized_environment(False)
        command = [
            "taskset",
            "-c",
            args.cpu_affinity,
            *legacy.backend_command(args.binary, args.target, args.query, 0, native),
        ]
        result = legacy.run_command(command, environment, args.timeout)
        legacy.write_backend_logs(native, result)
        report["command"] = command
        report["explicit_environment"] = explicit
        report["backend"] = result.report()
        if result.timed_out:
            raise CpuReferenceError("CPU authority timed out")
        if result.returncode != 0:
            raise CpuReferenceError(f"CPU authority exited {result.returncode}")
        try:
            tfosorted = legacy.validate_tfosorted(native, "authority")
        except legacy.WorkflowError as error:
            raise CpuReferenceError(str(error)) from error
        product = temporary / "product"
        diagnostics = product / "diagnostics"
        diagnostics.mkdir(parents=True)
        published_native = diagnostics / "native-TFOsorted"
        shutil.copy2(tfosorted, published_native)
        shutil.copy2(native / "wrapper-stdout.log", diagnostics / "backend-stdout.log")
        shutil.copy2(native / "wrapper-stderr.log", diagnostics / "backend-stderr.log")
        identity = identity_from_args(args)
        summary = candidate_sites.write_candidate_sites(
            query_fasta=args.query,
            target_fasta=args.target,
            tfosorted=published_native,
            destination=product / "candidate_sites.tsv",
            identity=identity,
            top_k=5,
        )
        receipt = candidate_sites.build_receipt(
            query=query,
            target=target,
            tfosorted=published_native,
            identity=identity,
        )
        receipt = replace(
            receipt,
            arm="A",
            evidence_role="v2_cpu_reference_offline_comparison",
        )
        legacy.atomic_json(product / "input-receipt.json", receipt_mapping(receipt))
        report["candidate_sites"] = summary
        report["input_pair_digest"] = receipt.input_identity["input_pair_digest"]
        report["status"] = "success"
        report["wall_seconds"] = time.perf_counter() - started
        os.replace(product, args.output)
        legacy.atomic_json(args.report, report)
        return report
    except Exception as error:
        report["status"] = "technical_failure"
        report["errors"].append(f"{type(error).__name__}: {error}")
        report["wall_seconds"] = time.perf_counter() - started
        legacy.atomic_json(args.report, report)
        raise
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--query", required=True, type=Path)
    result.add_argument("--target", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--report", required=True, type=Path)
    result.add_argument("--binary", type=Path, default=AUTHORITY_BINARY)
    result.add_argument("--timeout", type=int, default=3600)
    result.add_argument("--cpu-affinity", default="0-4,10-14")
    result.add_argument("--workload-id", required=True)
    result.add_argument("--query-ordinal-namespace", required=True)
    result.add_argument("--query-source-ordinal", required=True)
    result.add_argument("--target-ordinal-namespace", required=True)
    result.add_argument("--target-source-ordinal", required=True)
    result.add_argument("--assembly", required=True)
    result.add_argument("--target-coordinate-namespace", required=True)
    result.add_argument("--target-region-start0", required=True, type=int)
    result.add_argument("--query-extraction-recipe-id", required=True)
    result.add_argument("--target-extraction-recipe-id", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    for field in ("query", "target", "output", "report", "binary"):
        setattr(args, field, getattr(args, field).resolve())
    if args.timeout <= 0 or args.target_region_start0 < 0:
        print("CPU reference arguments are outside the frozen envelope", file=sys.stderr)
        return 2
    try:
        execute(args)
        return 0
    except (OSError, ValueError, CpuReferenceError, candidate_sites.CandidateSitesError) as error:
        print(f"CPU reference failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
