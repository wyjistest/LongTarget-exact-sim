#!/usr/bin/env python3
"""Execute the frozen Phase 4 CPU/GPU arm attempts without retries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
STATE = PAPER / "PROGRAM_STATE.json"
PLAN = PAPER / "phase_3_performance_plan.json"
ATTEMPT_MANIFEST = PAPER / "phase_3_attempt_manifest.tsv"
BINDING = PAPER / "phase_3_execution_binding.json"
FORMAL_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase4/formal"
PHASE4_ROOT = FORMAL_ROOT.parent
RUN_START = PHASE4_ROOT / "run-start.json"
CPU_RUNNER = ROOT / "reproduce/bioinformatics_submission_readiness_v2/cpu_reference_screen.py"
IMAGE_TAG = "longtarget/gasal2-gpu-screen:submission-rc-v2-2"
IMAGE_DIGEST = "sha256:f04340aa1b77092c25eee50c84144adb08e6f1b48a34580f6f9c33aff3163ca7"
PHASE3_COMMIT_SUBJECT = "repro: freeze v2 formal performance plan"
V2_ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2"

sys.path.insert(0, str(ROOT / "scripts"))

import gasal2_candidate_sites as candidate_sites  # noqa: E402
import gasal2_longtarget as legacy  # noqa: E402


class Phase4Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4Error(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    legacy.atomic_json(path, dict(value))


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def verify_launch_boundary() -> tuple[str, dict[str, Any]]:
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    require(status.returncode == 0 and not status.stdout.strip(), "Phase 4 requires a clean tree")
    subject = git("log", "-1", "--format=%s")
    require(subject.returncode == 0 and subject.stdout.strip() == PHASE3_COMMIT_SUBJECT, "HEAD is not the frozen Phase 3 commit")
    head = git("rev-parse", "HEAD")
    require(head.returncode == 0, "cannot resolve Phase 3 commit")
    state = load_json(STATE)
    require(state["active_phase"] == 4 and state["phase_status"]["3"] == "pass", "Phase 4 is not authorized by state")
    require(state["software_epoch"] == "submission_rc_v2_2", "formal software epoch drift")
    binding = load_json(BINDING)
    require(binding["schema_version"] == 1 and binding["phase"] == 3, "execution binding drift")
    for relative, expected in binding["execution_file_sha256"].items():
        path = ROOT / relative
        require(path.is_file() and sha256_file(path) == expected, f"Phase 3 execution file drift: {relative}")
    plan = load_json(PLAN)
    require(plan["formal_execution_authorized_after_phase3_commit"] is True, "formal execution is not authorized")
    require(plan["software_epoch"] == "submission_rc_v2_2", "performance plan epoch drift")
    image = subprocess.run(
        ("docker", "image", "inspect", IMAGE_TAG, "--format", "{{.Id}}"),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(image.returncode == 0 and image.stdout.strip() == IMAGE_DIGEST, "formal container image unavailable or drifted")
    return head.stdout.strip(), plan


def load_attempts() -> list[dict[str, str]]:
    with ATTEMPT_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    require(len(rows) == 100, "formal arm-attempt count drift")
    require([int(row["attempt_sequence_index"]) for row in rows] == list(range(1, 101)), "formal attempt order drift")
    require(len({row["attempt_id"] for row in rows}) == len(rows), "duplicate formal attempt ID")
    require(all(row["formal_status"] == "preregistered_not_run" for row in rows), "attempt manifest was outcome-edited")
    return rows


def validate_input(row: Mapping[str, str]) -> tuple[Path, Path]:
    query_path = ROOT / row["query_path"]
    target_path = ROOT / row["target_path"]
    query = candidate_sites.read_single_fasta(query_path, "query")
    target = candidate_sites.read_single_fasta(target_path, "target")
    require(len(query.sequence) == int(row["query_sequence_length"]), "formal query length drift")
    require(len(target.sequence) == int(row["target_sequence_length"]), "formal target length drift")
    require(candidate_sites.contract.sequence_sha256(query.sequence) == row["query_sequence_sha256"], "formal query digest drift")
    require(candidate_sites.contract.sequence_sha256(target.sequence) == row["target_sequence_sha256"], "formal target digest drift")
    require(set(query.sequence) <= set("ACGT") and set(target.sequence) <= set("ACGT"), "formal input alphabet drift")
    return query_path, target_path


def identity_arguments(row: Mapping[str, str]) -> list[str]:
    return [
        "--workload-id",
        row["workload_id"],
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


def cpu_command(row: Mapping[str, str], attempt: Path, query: Path, target: Path) -> list[str]:
    return [
        sys.executable,
        str(CPU_RUNNER),
        "--query",
        str(query),
        "--target",
        str(target),
        "--output",
        str(attempt / "product"),
        "--report",
        str(attempt / "run-report.json"),
        "--timeout",
        row["timeout_seconds"],
        "--cpu-affinity",
        row["cpu_affinity"],
        *identity_arguments(row),
    ]


def gpu_command(row: Mapping[str, str], attempt: Path, query: Path, target: Path) -> list[str]:
    container_name = f"v2-phase4-{row['attempt_id']}"
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--cpuset-cpus",
        row["cpu_affinity"],
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
        f"type=bind,src={query},dst=/inputs/query.fa,readonly",
        "--mount",
        f"type=bind,src={target},dst=/inputs/target.fa,readonly",
        "--mount",
        f"type=bind,src={attempt},dst=/attempt",
        IMAGE_TAG,
        "--query",
        "/inputs/query.fa",
        "--target",
        "/inputs/target.fa",
        "--output",
        "/attempt/product",
        "--report",
        "/attempt/run-report.json",
        "--timeout",
        row["timeout_seconds"],
        *identity_arguments(row),
    ]


def run_process(command: Sequence[str], *, timeout: int, stdout_path: Path, stderr_path: Path) -> dict[str, Any]:
    started_utc = legacy.utc_now()
    started = time.perf_counter()
    process = subprocess.Popen(
        list(command),
        cwd=ROOT,
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
        "started_utc": started_utc,
        "completed_utc": legacy.utc_now(),
        "returncode": 124 if timed_out else process.returncode,
        "timed_out": timed_out,
        "wall_seconds": time.perf_counter() - started,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
    }


def tree_file_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def check_artifact_budgets(plan: Mapping[str, Any]) -> dict[str, int]:
    budgets = plan["budgets"]
    total = tree_file_bytes(V2_ARTIFACT_ROOT)
    phase4 = tree_file_bytes(PHASE4_ROOT)
    require(total <= budgets["total_v2_artifact_bytes"], "v2 artifact quota exhausted")
    require(phase4 <= budgets["phase4_max_new_artifact_bytes"], "Phase 4 new-artifact quota exhausted")
    return {"total_v2_artifact_bytes": total, "phase4_new_artifact_bytes": phase4}


def verify_formal_gpu_is_idle(plan: Mapping[str, Any]) -> None:
    expected_index = plan["resources"]["gpu"]["gpu_index"]
    expected_uuid = plan["resources"]["gpu"]["gpu_uuid"]
    inventory = subprocess.run(
        ("nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader,nounits"),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(inventory.returncode == 0, "cannot inspect formal GPU identity")
    identities = {
        int(parts[0].strip()): parts[1].strip()
        for line in inventory.stdout.splitlines()
        if len(parts := line.split(",")) == 2
    }
    require(identities.get(expected_index) == expected_uuid, "formal GPU index/UUID mapping drift")
    completed = subprocess.run(
        (
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, "cannot inspect formal GPU occupancy")
    competing = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.split(",", 1)[0].strip() == expected_uuid
    ]
    require(not competing, f"formal GPU has a competing compute process: {competing}")


def load_or_create_run_start(phase3_commit: str) -> dict[str, Any]:
    if RUN_START.exists():
        receipt = load_json(RUN_START)
        require(receipt["phase3_commit"] == phase3_commit, "Phase 4 run-start commit drift")
        require(receipt["software_epoch"] == "submission_rc_v2_2", "Phase 4 run-start epoch drift")
        return receipt
    receipt = {
        "schema_version": 1,
        "phase": 4,
        "phase3_commit": phase3_commit,
        "software_epoch": "submission_rc_v2_2",
        "started_utc": legacy.utc_now(),
        "started_unix_seconds": time.time(),
    }
    atomic_json(RUN_START, receipt)
    return receipt


def phase4_elapsed_seconds(run_start: Mapping[str, Any]) -> float:
    elapsed = time.time() - float(run_start["started_unix_seconds"])
    require(elapsed >= 0, "system clock precedes the Phase 4 start receipt")
    return elapsed


def validate_product(row: Mapping[str, str], attempt: Path) -> dict[str, Any]:
    report_path = attempt / "run-report.json"
    sites_path = attempt / "product/candidate_sites.tsv"
    require(report_path.is_file() and sites_path.is_file(), "formal product/report missing")
    report = load_json(report_path)
    summary = candidate_sites.validate_candidate_sites(sites_path)
    require(summary["software_epoch"] == "submission_rc_v2_2", "formal product epoch drift")
    require(summary["scientific_contract"] == "biological_topk_candidate_site_v1", "formal product contract drift")
    require(summary["output_schema"] == "gasal2_candidate_sites_tsv_v1", "formal product schema drift")
    if row["arm"] == "A":
        require(report["status"] == "success", "CPU reference report failed")
        require(report["complete_cpu_authority_executed"] is True, "CPU authority was not complete")
    else:
        require(report["result_status"] == "release_candidate_under_test_complete", "GPU report failed")
        require(report["runtime_identity"]["container_image_digest"] == IMAGE_DIGEST, "GPU report image drift")
        require(report["runtime_identity"]["source_commit"] == "8114ce45be9bd5b25e52dc8fe7bc768eb6aee589", "GPU report source drift")
        require(report["backend_telemetry"]["fallbacks"] == 0, "GPU formal attempt used fallback")
        require(report["backend_telemetry"]["gasal2_requests"] > 0, "GPU formal attempt had no GPU requests")
    report_summary = report["candidate_sites"]
    require(report_summary["workload_id"] == row["workload_id"], "formal product workload drift")
    require(report_summary["sha256"] == summary["sha256"], "formal report/product digest drift")
    require(report_summary["row_count"] == summary["row_count"], "formal report/product row-count drift")
    return {
        "candidate_sites_sha256": summary["sha256"],
        "candidate_sites_rows": summary["row_count"],
        "run_report_sha256": sha256_file(report_path),
        "native_output_sha256": report_summary["native_output_sha256"],
    }


def execute_attempt(row: Mapping[str, str], *, phase3_commit: str) -> dict[str, Any]:
    destination = FORMAL_ROOT / row["attempt_id"]
    if destination.exists():
        terminal_path = destination / "attempt-terminal.json"
        require(terminal_path.is_file(), f"existing formal attempt lacks terminal receipt: {row['attempt_id']}")
        terminal = load_json(terminal_path)
        require(terminal["attempt_id"] == row["attempt_id"] and terminal["attempt_generation"] == 1, "formal terminal receipt drift")
        return terminal
    partial = FORMAL_ROOT / f".{row['attempt_id']}.partial"
    require(not partial.exists(), f"orphaned formal partial requires audit: {partial}")
    partial.mkdir(parents=True)
    query, target = validate_input(row)
    terminal: dict[str, Any] = {
        "schema_version": 1,
        "phase": 4,
        "formal": True,
        "attempt_id": row["attempt_id"],
        "attempt_sequence_index": int(row["attempt_sequence_index"]),
        "pair_id": row["pair_id"],
        "workload_id": row["workload_id"],
        "repeat_index": int(row["repeat_index"]),
        "arm": row["arm"],
        "arm_order": row["arm_order"],
        "attempt_generation": 1,
        "phase3_commit": phase3_commit,
        "software_epoch": "submission_rc_v2_2",
        "technical_success": False,
        "failure_reason": None,
        "input_identity": {
            "query_sequence_sha256": row["query_sequence_sha256"],
            "target_sequence_sha256": row["target_sequence_sha256"],
        },
        "execution": None,
        "product": None,
    }
    try:
        timeout = int(row["timeout_seconds"])
        command = (
            cpu_command(row, partial, query, target)
            if row["arm"] == "A"
            else gpu_command(row, partial, query, target)
        )
        execution = run_process(
            command,
            timeout=timeout + 30,
            stdout_path=partial / "runner-stdout.log",
            stderr_path=partial / "runner-stderr.log",
        )
        terminal["execution"] = execution
        require(not execution["timed_out"], "formal attempt timed out")
        require(execution["returncode"] == 0, f"formal attempt exited {execution['returncode']}")
        terminal["product"] = validate_product(row, partial)
        terminal["technical_success"] = True
    except Exception as error:
        terminal["failure_reason"] = f"{type(error).__name__}:{error}"
    terminal["terminal_utc"] = legacy.utc_now()
    atomic_json(partial / "attempt-terminal.json", terminal)
    os.replace(partial, destination)
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.parse_args()
    try:
        phase3_commit, plan = verify_launch_boundary()
        attempts = load_attempts()
        check_artifact_budgets(plan)
        verify_formal_gpu_is_idle(plan)
        FORMAL_ROOT.mkdir(parents=True, exist_ok=True)
        run_start = load_or_create_run_start(phase3_commit)
        check_artifact_budgets(plan)
        terminals = []
        for row in attempts:
            require(
                phase4_elapsed_seconds(run_start) <= plan["budgets"]["phase4_wall_seconds"],
                "Phase 4 wall budget exhausted",
            )
            check_artifact_budgets(plan)
            if row["arm"] == "G" and not (FORMAL_ROOT / row["attempt_id"]).exists():
                verify_formal_gpu_is_idle(plan)
            terminals.append(execute_attempt(row, phase3_commit=phase3_commit))
            check_artifact_budgets(plan)
            require(
                phase4_elapsed_seconds(run_start) <= plan["budgets"]["phase4_wall_seconds"],
                "Phase 4 wall budget exhausted",
            )
        summary = {
            "schema_version": 1,
            "phase": 4,
            "phase3_commit": phase3_commit,
            "planned_arm_attempts": len(attempts),
            "terminal_arm_attempts": len(terminals),
            "technical_success_arm_attempts": sum(item["technical_success"] for item in terminals),
            "technical_failure_arm_attempts": sum(not item["technical_success"] for item in terminals),
            "retry_count": 0,
            "formal_execution_complete": len(terminals) == len(attempts),
            "phase4_elapsed_seconds": phase4_elapsed_seconds(run_start),
            "artifact_bytes": check_artifact_budgets(plan),
            "completed_utc": legacy.utc_now(),
        }
        atomic_json(PHASE4_ROOT / "run-summary.json", summary)
        check_artifact_budgets(plan)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, Phase4Error, candidate_sites.CandidateSitesError) as error:
        print(f"Phase 4 execution failed closed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0 if summary["technical_failure_arm_attempts"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
