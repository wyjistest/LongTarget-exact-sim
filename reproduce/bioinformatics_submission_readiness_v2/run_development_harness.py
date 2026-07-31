#!/usr/bin/env python3
"""Run excluded CPU/GPU pairs through the v2 candidate-site contract harness."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "reproduce/bioinformatics_submission_readiness_v2"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase2/development-harness"
HISTORICAL_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/fresh-holdout"
HISTORICAL_MANIFEST = ROOT / "paper/biological_topk_successor/fresh_holdout_manifest.tsv"
CONTRACT_SPEC = ROOT / "paper/biological_topk/contract_spec.json"
COMPARATOR = ROOT / "reproduce/biological_topk/compare_candidate_topk.py"
CPU_RUNNER = SCRIPT_ROOT / "cpu_reference_screen.py"
IMAGE_TAG = "longtarget/gasal2-gpu-screen:submission-rc-v2-2"
IMAGE_DIGEST = "sha256:f04340aa1b77092c25eee50c84144adb08e6f1b48a34580f6f9c33aff3163ca7"
DEFAULT_WORKLOADS = ("bts3_w022", "bts3_w006", "bts3_w153")

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SCRIPT_ROOT))

import gasal2_candidate_sites as candidate_sites  # noqa: E402
import gasal2_longtarget as legacy  # noqa: E402
from cpu_reference_screen import receipt_mapping  # noqa: E402


class HarnessError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    legacy.atomic_json(path, dict(value))


def load_manifest() -> dict[str, dict[str, str]]:
    with HISTORICAL_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {row["workload_id"]: row for row in rows}


def source_inputs(workload_id: str) -> tuple[Path, Path]:
    root = HISTORICAL_ROOT / f"{workload_id}__repeat00_a/inputs"
    return root / "query.fa", root / "target.fa"


def product_identity(row: Mapping[str, str], workload_id: str) -> candidate_sites.ProductIdentity:
    return candidate_sites.ProductIdentity(
        workload_id=workload_id,
        query_ordinal_namespace=row["query_ordinal_namespace"],
        query_source_ordinal=row["query_source_ordinal"],
        target_ordinal_namespace=row["target_ordinal_namespace"],
        target_source_ordinal=row["target_source_ordinal"],
        assembly=row["assembly"],
        target_coordinate_namespace=row["target_coordinate_namespace"],
        query_extraction_recipe_id=row["query_extraction_recipe_id"],
        target_extraction_recipe_id=row["target_extraction_recipe_id"],
        target_region_start0=int(row["target_region_start0"]),
    )


def identity_arguments(row: Mapping[str, str], workload_id: str) -> list[str]:
    return [
        "--workload-id",
        workload_id,
        "--query-ordinal-namespace",
        row["query_ordinal_namespace"],
        "--query-source-ordinal",
        row["query_source_ordinal"],
        "--target-ordinal-namespace",
        row["target_ordinal_namespace"],
        "--target-source-ordinal",
        row["target_source_ordinal"],
        "--assembly",
        row["assembly"],
        "--target-coordinate-namespace",
        row["target_coordinate_namespace"],
        "--target-region-start0",
        row["target_region_start0"],
        "--query-extraction-recipe-id",
        row["query_extraction_recipe_id"],
        "--target-extraction-recipe-id",
        row["target_extraction_recipe_id"],
    ]


def run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return {
        "command": list(command),
        "returncode": 124 if timed_out else process.returncode,
        "timed_out": timed_out,
        "wall_seconds": time.perf_counter() - started,
        "stdout_sha256": legacy.sha256(stdout_path),
        "stderr_sha256": legacy.sha256(stderr_path),
    }


def cpu_command(root: Path, row: Mapping[str, str], workload_id: str, timeout: int, affinity: str) -> list[str]:
    return [
        sys.executable,
        str(CPU_RUNNER),
        "--query",
        str(root / "inputs/query.fa"),
        "--target",
        str(root / "inputs/target.fa"),
        "--output",
        str(root / "cpu-product"),
        "--report",
        str(root / "cpu-report.json"),
        "--timeout",
        str(timeout),
        "--cpu-affinity",
        affinity,
        *identity_arguments(row, workload_id),
    ]


def gpu_command(root: Path, row: Mapping[str, str], workload_id: str, timeout: int, affinity: str) -> list[str]:
    container_name = f"v2-dev-{workload_id}-{os.getpid()}"
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--cpuset-cpus",
        affinity,
        "--device",
        "/dev/nvidia0",
        "--device",
        "/dev/nvidiactl",
        "--device",
        "/dev/nvidia-uvm",
        "--device",
        "/dev/nvidia-uvm-tools",
        "-e",
        "CUDA_VISIBLE_DEVICES=0",
        "-e",
        f"GASAL2_GPU_SCREEN_CONTAINER_DIGEST={IMAGE_DIGEST}",
        "--mount",
        "type=bind,src=/usr/bin/nvidia-smi,dst=/usr/bin/nvidia-smi,readonly",
        "--mount",
        "type=bind,src=/usr/lib/x86_64-linux-gnu,dst=/usr/lib/x86_64-linux-gnu,readonly",
        "--mount",
        f"type=bind,src={root},dst=/attempt",
        IMAGE_TAG,
        "--query",
        "/attempt/inputs/query.fa",
        "--target",
        "/attempt/inputs/target.fa",
        "--output",
        "/attempt/gpu-product",
        "--report",
        "/attempt/gpu-report.json",
        "--timeout",
        str(timeout),
        *identity_arguments(row, workload_id),
    ]


def write_gpu_receipt(root: Path, row: Mapping[str, str], workload_id: str) -> Path:
    identity = product_identity(row, workload_id)
    query = candidate_sites.read_single_fasta(root / "inputs/query.fa", "query")
    target = candidate_sites.read_single_fasta(root / "inputs/target.fa", "target")
    receipt = candidate_sites.build_receipt(
        query=query,
        target=target,
        tfosorted=root / "gpu-product/diagnostics/native-TFOsorted",
        identity=identity,
    )
    receipt = replace(receipt, evidence_role="v2_gpu_screen_offline_comparison")
    report = json.loads((root / "gpu-report.json").read_text(encoding="utf-8"))
    require(
        receipt.input_identity["input_pair_digest"]
        == report["candidate_sites"]["input_pair_digest"],
        "GPU receipt/report pair identity mismatch",
    )
    destination = root / "gpu-input-receipt.json"
    atomic_json(destination, receipt_mapping(receipt))
    return destination


def validate_preflight(root: Path, row: Mapping[str, str]) -> None:
    query = candidate_sites.read_single_fasta(root / "inputs/query.fa", "query")
    target = candidate_sites.read_single_fasta(root / "inputs/target.fa", "target")
    require(set(query.sequence) <= set("ACGT"), "query contains a non-ACGT base")
    require(set(target.sequence) <= set("ACGT"), "target contains a non-ACGT base")
    require(len(query.sequence) == int(row["query_sequence_length"]), "query length drift")
    require(len(target.sequence) == int(row["target_sequence_length"]), "target length drift")
    require(candidate_sites.contract.sequence_sha256(query.sequence) == row["query_sequence_sha256"], "query digest drift")
    require(candidate_sites.contract.sequence_sha256(target.sequence) == row["target_sequence_sha256"], "target digest drift")


def execute_pair(row: Mapping[str, str], *, timeout: int, affinity: str) -> dict[str, Any]:
    source_id = row["workload_id"]
    workload_id = f"phase2_dev_{source_id}"
    destination = ARTIFACT_ROOT / workload_id
    if destination.exists():
        terminal = destination / "pair-complete.json"
        require(terminal.is_file(), "existing development attempt lacks terminal receipt")
        return json.loads(terminal.read_text(encoding="utf-8"))
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    partial = Path(tempfile.mkdtemp(prefix=f".{workload_id}.partial.", dir=ARTIFACT_ROOT))
    (partial / "inputs").mkdir()
    query_source, target_source = source_inputs(source_id)
    shutil.copy2(query_source, partial / "inputs/query.fa")
    shutil.copy2(target_source, partial / "inputs/target.fa")
    pair: dict[str, Any] = {
        "schema_version": 1,
        "workload_id": workload_id,
        "source_workload_id": source_id,
        "development_diagnostic_only": True,
        "excluded_from_all_v2_formal_panels": True,
        "status": "running",
        "failure_reason": None,
        "arms": {},
        "comparison": None,
    }
    try:
        validate_preflight(partial, row)
        for arm, command in (
            ("A", cpu_command(partial, row, workload_id, timeout, affinity)),
            ("G", gpu_command(partial, row, workload_id, timeout, affinity)),
        ):
            execution = run_process(
                command,
                cwd=ROOT,
                timeout=timeout + 30,
                stdout_path=partial / f"{arm.lower()}-runner-stdout.log",
                stderr_path=partial / f"{arm.lower()}-runner-stderr.log",
            )
            pair["arms"][arm] = execution
            require(not execution["timed_out"], f"{arm} arm timed out")
            require(execution["returncode"] == 0, f"{arm} arm exited {execution['returncode']}")
        gpu_receipt = write_gpu_receipt(partial, row, workload_id)
        comparison_command = [
            sys.executable,
            str(COMPARATOR),
            "--authority",
            str(partial / "cpu-product/diagnostics/native-TFOsorted"),
            "--candidate",
            str(partial / "gpu-product/diagnostics/native-TFOsorted"),
            "--authority-receipt",
            str(partial / "cpu-product/input-receipt.json"),
            "--candidate-receipt",
            str(gpu_receipt),
            "--contract-spec",
            str(CONTRACT_SPEC),
            "--output-json",
            str(partial / "comparison.json"),
            "--details-tsv",
            str(partial / "comparison-details.tsv"),
        ]
        comparison_execution = run_process(
            comparison_command,
            cwd=ROOT,
            timeout=300,
            stdout_path=partial / "comparison-stdout.log",
            stderr_path=partial / "comparison-stderr.log",
        )
        comparison = json.loads((partial / "comparison.json").read_text(encoding="utf-8"))
        pair["comparison"] = {
            "execution": comparison_execution,
            "result": comparison,
        }
        require(comparison_execution["returncode"] == 0, "candidate-site comparator rejected pair")
        require(comparison["contract_pass"] is True, "candidate-site contract did not pass")
        authority_seconds = float(pair["arms"]["A"]["wall_seconds"])
        gpu_seconds = float(pair["arms"]["G"]["wall_seconds"])
        pair["diagnostic_paired_speedup"] = authority_seconds / gpu_seconds
        pair["status"] = "development_pass"
    except Exception as error:
        pair["status"] = "development_failure"
        pair["failure_reason"] = f"{type(error).__name__}:{error}"
    pair["completed_utc"] = legacy.utc_now()
    atomic_json(partial / "pair-complete.json", pair)
    os.replace(partial, destination)
    return pair


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workloads", default=",".join(DEFAULT_WORKLOADS))
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--cpu-affinity", default="0-4,10-14")
    args = parser.parse_args()
    requested = tuple(item for item in args.workloads.split(",") if item)
    manifest = load_manifest()
    if not requested or any(item not in manifest for item in requested):
        print("development workload selection is empty or unknown", file=sys.stderr)
        return 2
    results = [
        execute_pair(manifest[workload_id], timeout=args.timeout, affinity=args.cpu_affinity)
        for workload_id in requested
    ]
    summary = {
        "schema_version": 1,
        "development_diagnostic_only": True,
        "formal_claim": False,
        "workload_count": len(results),
        "pass_count": sum(row["status"] == "development_pass" for row in results),
        "failure_count": sum(row["status"] != "development_pass" for row in results),
        "results": results,
    }
    atomic_json(ARTIFACT_ROOT / "development-summary.json", summary)
    display = {
        "schema_version": 1,
        "development_diagnostic_only": True,
        "workload_count": summary["workload_count"],
        "pass_count": summary["pass_count"],
        "failure_count": summary["failure_count"],
        "results": [
            {
                "workload_id": row["workload_id"],
                "status": row["status"],
                "failure_reason": row["failure_reason"],
                "diagnostic_paired_speedup": row.get("diagnostic_paired_speedup"),
                "comparison_status": (
                    None
                    if row.get("comparison") is None
                    else row["comparison"]["result"]["comparison_status"]
                ),
            }
            for row in results
        ],
    }
    print(json.dumps(display, indent=2, sort_keys=True, allow_nan=False))
    return 0 if summary["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
