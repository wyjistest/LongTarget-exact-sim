#!/usr/bin/env python3
"""GPU-only candidate-site screening release candidate under test."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import gasal2_candidate_sites as candidate_sites  # noqa: E402
import gasal2_longtarget as legacy  # noqa: E402


VERSION = "0.1.0-rc.1"
REPORT_SCHEMA_VERSION = "1.0.0"
EXECUTION_MODE = "gpu-screen"
VALIDATION_STATUS = "pending_phase4"
DEFAULT_BINARY = (
    SCRIPT_DIR / "bin/fasim_longtarget_gasal2"
    if (SCRIPT_DIR / "bin/fasim_longtarget_gasal2").is_file()
    else REPOSITORY_ROOT / "fasim_longtarget_gasal2"
)
REPORT_SCHEMA = (
    SCRIPT_DIR / "schemas/gasal2_gpu_screen_run_report_v1.schema.json"
    if (SCRIPT_DIR / "schemas/gasal2_gpu_screen_run_report_v1.schema.json").is_file()
    else REPOSITORY_ROOT / "schemas/gasal2_gpu_screen_run_report_v1.schema.json"
)
EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
EXIT_ENVIRONMENT = 3
EXIT_BACKEND_FAILURE = 5
EXIT_PRODUCT_FAILURE = 6
EXIT_INTERNAL = 7
EXIT_INTERRUPTED = 130


class GpuScreenError(RuntimeError):
    def __init__(self, message: str, exit_code: int, result_status: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.result_status = result_status


def _runtime_identity(args: argparse.Namespace) -> dict[str, Any]:
    observed = {
        "source_commit": legacy.git_commit(),
        "binary_path": str(args.candidate_binary),
        "binary_sha256": legacy.sha256(args.candidate_binary) if args.candidate_binary.is_file() else None,
        "container_image_digest": os.environ.get("GASAL2_GPU_SCREEN_CONTAINER_DIGEST"),
        "runtime_identity_path": None,
    }
    if args.runtime_identity is None:
        return observed
    if not args.runtime_identity.is_file() or args.runtime_identity.is_symlink():
        raise GpuScreenError(
            f"missing or unsafe runtime identity: {args.runtime_identity}",
            EXIT_INVALID_INPUT,
            "invalid_input",
        )
    try:
        frozen = json.loads(args.runtime_identity.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GpuScreenError(
            f"invalid runtime identity: {error}", EXIT_INVALID_INPUT, "invalid_input"
        ) from error
    required = {
        "execution_mode": EXECUTION_MODE,
        "scientific_contract": candidate_sites.SCIENTIFIC_CONTRACT,
        "output_schema": candidate_sites.OUTPUT_SCHEMA,
        "software_epoch": candidate_sites.SOFTWARE_EPOCH,
    }
    for field, expected in required.items():
        if frozen.get(field) != expected:
            raise GpuScreenError(
                f"runtime identity {field} drift", EXIT_INVALID_INPUT, "invalid_input"
            )
    digest = legacy.sha256(args.candidate_binary) if args.candidate_binary.is_file() else None
    if frozen.get("candidate_binary_sha256") != digest:
        raise GpuScreenError(
            "candidate binary digest does not match runtime identity",
            EXIT_ENVIRONMENT,
            "environment_unavailable",
        )
    return {
        "source_commit": frozen.get("implementation_commit"),
        "binary_path": str(args.candidate_binary),
        "binary_sha256": digest,
        "container_image_digest": frozen.get("container_image_digest")
        or os.environ.get("GASAL2_GPU_SCREEN_CONTAINER_DIGEST"),
        "runtime_identity_path": str(args.runtime_identity),
    }


def _base_report(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "software_version": VERSION,
        "execution_identity": {
            "execution_mode": EXECUTION_MODE,
            "scientific_contract": candidate_sites.SCIENTIFIC_CONTRACT,
            "output_schema": candidate_sites.OUTPUT_SCHEMA,
            "software_epoch": candidate_sites.SOFTWARE_EPOCH,
            "artifact_role": "frozen_release_candidate_under_test",
            "validation_status": VALIDATION_STATUS,
        },
        "runtime_identity": {
            "source_commit": None,
            "binary_path": str(args.candidate_binary),
            "binary_sha256": None,
            "container_image_digest": None,
            "runtime_identity_path": None,
        },
        "result_status": "preflight_pending",
        "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "inputs": {
            "query": {"path": str(args.query), "sha256": None, "length": None},
            "target": {"path": str(args.target), "sha256": None, "length": None},
        },
        "product_identity": {
            "workload_id": args.workload_id,
            "query_ordinal_namespace": args.query_ordinal_namespace,
            "query_source_ordinal": args.query_source_ordinal,
            "target_ordinal_namespace": args.target_ordinal_namespace,
            "target_source_ordinal": args.target_source_ordinal,
            "assembly": args.assembly,
            "target_coordinate_namespace": args.target_coordinate_namespace,
            "target_region_start0": args.target_region_start0,
        },
        "environment": {
            "cpu_model": legacy.cpu_model(),
            "cpu_thread_count": os.cpu_count(),
            "gpus": [],
            "gpu_count": None,
            "candidate_contract_environment": {},
        },
        "preflight": {"passed": False, "checks": {}, "errors": []},
        "backend": None,
        "backend_telemetry": None,
        "candidate_sites": None,
        "published_outputs": [],
        "timestamps": {"start_utc": legacy.utc_now(), "end_utc": None, "wall_seconds": None},
        "warnings": [
            "release candidate is frozen under test; final validation is pending Phase 4"
        ],
        "errors": [],
    }


def _finish(report: dict[str, Any], started: float) -> None:
    report["timestamps"]["end_utc"] = legacy.utc_now()
    report["timestamps"]["wall_seconds"] = time.perf_counter() - started


def _validate_report(report: dict[str, Any]) -> None:
    try:
        schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
        legacy.validate_schema_value(schema, report, "report")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GpuScreenError(
            f"run report schema validation failed: {error}", EXIT_INTERNAL, "internal_error"
        ) from error


def _check_destinations(args: argparse.Namespace) -> None:
    if args.report == args.output or args.output in args.report.parents:
        raise GpuScreenError(
            "--report must be outside --output", EXIT_INVALID_INPUT, "invalid_input"
        )
    if args.output.exists() and not args.force:
        raise GpuScreenError(
            f"output already exists: {args.output}", EXIT_INVALID_INPUT, "invalid_input"
        )
    if args.report.exists() and not args.force:
        raise GpuScreenError(
            f"report already exists: {args.report}", EXIT_INVALID_INPUT, "invalid_input"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)


def _parse_backend_telemetry(stderr: str) -> dict[str, int]:
    keys = {
        "benchmark.fasim_top5_gasal2_gpu_scoreinfo_requested": "gpu_scoreinfo_requested",
        "benchmark.fasim_top5_gasal2_gpu_scoreinfo_active": "gpu_scoreinfo_active",
        "benchmark.fasim_gasal2_enabled": "gasal2_enabled",
        "benchmark.fasim_gasal2_built": "gasal2_built",
        "benchmark.fasim_gasal2_requests": "gasal2_requests",
        "benchmark.fasim_gasal2_fallbacks": "fallbacks",
    }
    values: dict[str, set[int]] = {field: set() for field in keys.values()}
    for raw in stderr.splitlines():
        if "=" not in raw:
            continue
        name, value = raw.split("=", 1)
        if name not in keys:
            continue
        try:
            parsed = int(value)
        except ValueError as error:
            raise GpuScreenError(
                f"noninteger backend telemetry {name}", EXIT_PRODUCT_FAILURE, "telemetry_failure"
            ) from error
        values[keys[name]].add(parsed)
    missing = sorted(field for field, observed in values.items() if not observed)
    conflicting = sorted(field for field, observed in values.items() if len(observed) != 1)
    if missing or conflicting:
        raise GpuScreenError(
            f"backend telemetry incomplete or conflicting: missing={missing}, conflicting={conflicting}",
            EXIT_PRODUCT_FAILURE,
            "telemetry_failure",
        )
    result = {field: next(iter(observed)) for field, observed in values.items()}
    if any(result[field] != 1 for field in ("gpu_scoreinfo_requested", "gpu_scoreinfo_active", "gasal2_enabled", "gasal2_built")):
        raise GpuScreenError(
            "GPU score path was not active", EXIT_PRODUCT_FAILURE, "telemetry_failure"
        )
    if result["gasal2_requests"] <= 0:
        raise GpuScreenError(
            "GPU backend reported no GASAL2 requests", EXIT_PRODUCT_FAILURE, "telemetry_failure"
        )
    if result["fallbacks"] != 0:
        raise GpuScreenError(
            "GPU backend used an unexpected fallback", EXIT_PRODUCT_FAILURE, "unexpected_fallback"
        )
    return result


def _collect_outputs(stage: Path, final: Path) -> list[dict[str, Any]]:
    outputs = []
    for path in sorted(item for item in stage.rglob("*") if item.is_file()):
        relative = path.relative_to(stage)
        records = None
        if path.suffix == ".tsv" or path.name.endswith("TFOsorted"):
            records = max(len(path.read_text(encoding="utf-8").splitlines()) - 1, 0)
        outputs.append(
            {
                "path": str(final / relative),
                "relative_path": relative.as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": legacy.sha256(path),
                "record_count": records,
            }
        )
    return outputs


def _publish(
    *, stage: Path, report: dict[str, Any], args: argparse.Namespace, temporary_root: Path
) -> None:
    report["published_outputs"] = _collect_outputs(stage, args.output)
    _validate_report(report)
    backup = None
    if args.output.exists():
        backup = args.output.parent / f".{args.output.name}.backup.{os.getpid()}"
        os.replace(args.output, backup)
    try:
        os.replace(stage, args.output)
        legacy.atomic_json(args.report, report)
    except Exception:
        shutil.rmtree(args.output, ignore_errors=True)
        if backup is not None:
            os.replace(backup, args.output)
        raise
    else:
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def execute(args: argparse.Namespace, report: dict[str, Any], started: float) -> int:
    _check_destinations(args)
    try:
        query = legacy.parse_fasta(args.query, "query")
        target = legacy.parse_fasta(args.target, "target")
    except legacy.WorkflowError as error:
        raise GpuScreenError(str(error), EXIT_INVALID_INPUT, "invalid_input") from error
    if query["record_count"] != 1 or target["record_count"] != 1:
        raise GpuScreenError(
            "gpu-screen requires exactly one query and one target FASTA record",
            EXIT_INVALID_INPUT,
            "invalid_input",
        )
    report["inputs"] = {
        "query": {"path": query["path"], "sha256": query["sha256"], "length": query["length_max"]},
        "target": {"path": target["path"], "sha256": target["sha256"], "length": target["length_max"]},
    }
    gpus = legacy.detect_gpus()
    report["environment"]["gpus"] = gpus
    report["environment"]["gpu_count"] = len(gpus)
    eligibility = legacy.gpu_eligibility(query, target, args.candidate_binary, gpus)
    if eligibility:
        raise GpuScreenError(
            "; ".join(eligibility), EXIT_ENVIRONMENT, "environment_unavailable"
        )
    report["runtime_identity"] = _runtime_identity(args)
    environment, contract_environment = legacy.sanitized_environment(True)
    forbidden = {
        "FASIM_CANONICAL_HYBRID_V2",
        "FASIM_ALIGN_GASAL2_CPU_TRACEBACK",
        "FASIM_ALIGN_GASAL2_CPU_TRACEBACK_ALL",
    }
    if forbidden & set(contract_environment):
        raise GpuScreenError(
            "gpu-screen environment contains a hybrid or complete-authority route",
            EXIT_INTERNAL,
            "internal_error",
        )
    report["environment"]["candidate_contract_environment"] = contract_environment
    report["preflight"] = {
        "passed": True,
        "checks": {
            "single_query_record": True,
            "single_target_record": True,
            "query_within_2812_nt": True,
            "candidate_binary_available": True,
            "gpu_environment_eligible": True,
            "complete_cpu_authority_not_configured": True,
            "output_schema_fixed": True,
        },
        "errors": [],
    }
    if args.dry_run:
        report["result_status"] = "dry_run"
        _finish(report, started)
        _validate_report(report)
        legacy.atomic_json(args.report, report)
        return EXIT_SUCCESS

    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.partial.", dir=args.output.parent)
    )
    native = temporary_root / "native"
    native.mkdir()
    try:
        result = legacy.run_command(
            legacy.backend_command(args.candidate_binary, args.target, args.query, 0, native),
            environment,
            args.timeout,
        )
        legacy.write_backend_logs(native, result)
        report["backend"] = result.report()
        if result.timed_out:
            raise GpuScreenError("candidate backend timed out", EXIT_BACKEND_FAILURE, "backend_failure")
        if result.returncode != 0:
            raise GpuScreenError(
                f"candidate backend exited {result.returncode}", EXIT_BACKEND_FAILURE, "backend_failure"
            )
        try:
            tfosorted = legacy.validate_tfosorted(native, "candidate")
        except legacy.WorkflowError as error:
            raise GpuScreenError(str(error), EXIT_BACKEND_FAILURE, "backend_failure") from error
        report["backend_telemetry"] = _parse_backend_telemetry(result.stderr)
        product = temporary_root / "published"
        diagnostics = product / "diagnostics"
        diagnostics.mkdir(parents=True)
        shutil.copy2(tfosorted, diagnostics / "native-TFOsorted")
        shutil.copy2(native / "wrapper-stdout.log", diagnostics / "backend-stdout.log")
        shutil.copy2(native / "wrapper-stderr.log", diagnostics / "backend-stderr.log")
        identity = candidate_sites.ProductIdentity(
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
        summary = candidate_sites.write_candidate_sites(
            query_fasta=args.query,
            target_fasta=args.target,
            tfosorted=tfosorted,
            destination=product / "candidate_sites.tsv",
            identity=identity,
            top_k=5,
        )
        report["candidate_sites"] = summary
        legacy.atomic_json(
            product / "contract.json",
            {
                "schema_version": 1,
                "execution_mode": EXECUTION_MODE,
                "scientific_contract": candidate_sites.SCIENTIFIC_CONTRACT,
                "output_schema": candidate_sites.OUTPUT_SCHEMA,
                "software_epoch": candidate_sites.SOFTWARE_EPOCH,
                "artifact_role": "frozen_release_candidate_under_test",
                "validation_status": VALIDATION_STATUS,
                "complete_cpu_authority_executed": False,
                "native_output_role": "diagnostic_only_no_full_row_claim",
                "candidate_sites_sha256": summary["sha256"],
                "candidate_sites_rows": summary["row_count"],
                "input_pair_digest": summary["input_pair_digest"],
            },
        )
        report["result_status"] = "release_candidate_under_test_complete"
        _finish(report, started)
        _publish(stage=product, report=report, args=args, temporary_root=temporary_root)
        return EXIT_SUCCESS
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="gasal2-gpu-screen",
        description="GPU-only short-query candidate-site screening release candidate under test.",
    )
    result.add_argument("--version", action="version", version=f"gasal2-gpu-screen {VERSION}")
    result.add_argument("--query", required=True, type=Path)
    result.add_argument("--target", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--report", required=True, type=Path)
    result.add_argument("--candidate-binary", type=Path, default=DEFAULT_BINARY)
    result.add_argument(
        "--runtime-identity",
        type=Path,
        default=os.environ.get("GASAL2_GPU_SCREEN_RUNTIME_IDENTITY"),
    )
    result.add_argument("--timeout", type=int, default=3600)
    result.add_argument("--force", action="store_true")
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--workload-id")
    result.add_argument("--query-ordinal-namespace", default="user_query_fasta_header_v1")
    result.add_argument("--query-source-ordinal")
    result.add_argument("--target-ordinal-namespace", default="user_target_fasta_header_v1")
    result.add_argument("--target-source-ordinal")
    result.add_argument("--assembly", default="unspecified")
    result.add_argument("--target-coordinate-namespace", default="target_fasta_0_based_half_open")
    result.add_argument("--target-region-start0", type=int, default=0)
    result.add_argument("--query-extraction-recipe-id", default="full_single_record_fasta_v1")
    result.add_argument("--target-extraction-recipe-id", default="full_single_record_fasta_v1")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.timeout <= 0:
        parser().error("--timeout must be positive")
    if args.target_region_start0 < 0:
        parser().error("--target-region-start0 must be nonnegative")
    for attribute in ("query", "target", "output", "report", "candidate_binary", "runtime_identity"):
        value = getattr(args, attribute)
        if value is not None:
            setattr(args, attribute, value.resolve())
    started = time.perf_counter()
    report = _base_report(args)
    old_sigint = signal.getsignal(signal.SIGINT)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, legacy._signal_handler)
    signal.signal(signal.SIGTERM, legacy._signal_handler)
    report_allowed = not args.report.exists() or args.force
    try:
        return execute(args, report, started)
    except legacy.WorkflowInterrupted as error:
        report["result_status"] = "interrupted"
        report["errors"].append(str(error))
        _finish(report, started)
        if report_allowed:
            try:
                _validate_report(report)
                legacy.atomic_json(args.report, report)
            except Exception:
                pass
        return EXIT_INTERRUPTED
    except (GpuScreenError, candidate_sites.CandidateSitesError) as error:
        if isinstance(error, GpuScreenError):
            exit_code = error.exit_code
            result_status = error.result_status
        else:
            exit_code = EXIT_PRODUCT_FAILURE
            result_status = "product_output_failure"
        report["result_status"] = result_status
        report["errors"].append(str(error))
        _finish(report, started)
        if report_allowed:
            try:
                _validate_report(report)
                legacy.atomic_json(args.report, report)
            except Exception as report_error:
                print(f"failed to write run report: {report_error}", file=sys.stderr)
                return EXIT_INTERNAL
        print(str(error), file=sys.stderr)
        return exit_code
    except Exception as error:
        legacy._kill_active_child()
        report["result_status"] = "internal_error"
        report["errors"].append(f"{type(error).__name__}: {error}")
        _finish(report, started)
        if report_allowed:
            try:
                _validate_report(report)
                legacy.atomic_json(args.report, report)
            except Exception:
                pass
        print(f"internal error: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_INTERNAL
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)


if __name__ == "__main__":
    raise SystemExit(main())
