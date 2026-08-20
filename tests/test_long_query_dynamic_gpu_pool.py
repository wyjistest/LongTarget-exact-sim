#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "long_query_dynamic_gpu_pool.py"
SPEC = importlib.util.spec_from_file_location("long_query_dynamic_gpu_pool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
POOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POOL)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class DynamicGpuPoolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="longtarget-pool-test-")
        self.base = Path(self.temporary.name)
        self.pool_root = self.base / "pool"
        self.results_root = self.base / "results"
        self.query = self.base / "query.fa"
        self.query.write_text(">query\nACGTACGT\n", encoding="ascii")
        self.query_file_sha = POOL.sha256_file(self.query)
        self.query_sequence_sha = digest_bytes(b"ACGTACGT")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_plan(
        self,
        estimates: list[float],
        *,
        max_attempts: int = 2,
        lease_seconds: float = 60.0,
        runner_command: list[str] | None = None,
    ) -> Path:
        manifest = self.base / "manifest.tsv"
        lines = [
            "job_id\tgene_id\tquery_length_nt\testimated_seconds\tquery_path\tquery_file_sha256\tquery_sequence_sha256"
        ]
        for index, estimate in enumerate(estimates, 1):
            lines.append(
                "\t".join(
                    (
                        f"job{index}",
                        f"ENSG{index:011d}",
                        "8",
                        str(estimate),
                        str(self.query),
                        self.query_file_sha,
                        self.query_sequence_sha,
                    )
                )
            )
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if runner_command is None:
            runner_command = ["/bin/true"]
        plan = {
            "schema_version": POOL.PLAN_SCHEMA,
            "pool_id": "test-pool",
            "manifest": {
                "path": str(manifest),
                "sha256": POOL.sha256_file(manifest),
            },
            "results_root": str(self.results_root),
            "lease_seconds": lease_seconds,
            "heartbeat_seconds": max(0.01, lease_seconds / 4.0),
            "worker_stale_seconds": max(0.04, lease_seconds),
            "poll_seconds": 0.01,
            "max_attempts": max_attempts,
            "workers": [
                {
                    "worker_id": "gpu0",
                    "gpu_id": "0",
                    "gpu_uuid": "GPU-test-0",
                    "cpu_affinity": "0,2",
                    "runtime_model": {
                        "intercept_seconds": 0,
                        "coefficients": {"estimated_seconds": 1.0},
                    },
                },
                {
                    "worker_id": "gpu1",
                    "gpu_id": "1",
                    "gpu_uuid": "GPU-test-1",
                    "cpu_affinity": "1,3",
                    "runtime_model": {
                        "intercept_seconds": 0,
                        "coefficients": {"estimated_seconds": 2.0},
                    },
                },
            ],
            "runner": {"command": runner_command, "environment": {}},
            "receipt_contract": {
                "source_commit": "a438ccf-test",
                "binary_sha256": "binary-test-digest",
                "target_sha256": "target-test-digest",
                "execution_mode": "consumer_driven_f1_exact_pipeline",
            },
        }
        plan_path = self.base / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        return plan_path

    def initialize(self, estimates: list[float], **kwargs: object) -> Path:
        plan = self.write_plan(estimates, **kwargs)
        POOL.initialize_pool(self.pool_root, plan)
        return plan

    def state(self) -> dict[str, object]:
        return POOL.read_json(self.pool_root / "state.json")

    def write_state(self, state: dict[str, object]) -> None:
        POOL.atomic_json(self.pool_root / "state.json", state)

    def write_publish(
        self,
        claim: dict[str, object],
        content: bytes = b"exact-output\n",
        *,
        destination: Path | None = None,
        wall_seconds: float = 1.25,
    ) -> Path:
        if destination is None:
            state = self.state()
            job = state["jobs"][claim["job_id"]]  # type: ignore[index]
            destination = Path(job["attempt_dir"]) / "publish"  # type: ignore[index]
        destination.mkdir(parents=True)
        artifact = destination / "result-TFOsorted"
        artifact.write_bytes(content)
        receipt = {
            "schema_version": POOL.RECEIPT_SCHEMA,
            "status": "complete",
            "pool_id": claim["pool_id"],
            "job_id": claim["job_id"],
            "gene_id": claim["gene_id"],
            "worker_id": claim["worker_id"],
            "lease_epoch": claim["lease_epoch"],
            "query_file_sha256": claim["row"]["query_file_sha256"],  # type: ignore[index]
            "query_sequence_sha256": claim["row"]["query_sequence_sha256"],  # type: ignore[index]
            "artifact_path": artifact.name,
            "artifact_size_bytes": len(content),
            "artifact_sha256": digest_bytes(content),
            "wall_seconds": wall_seconds,
        }
        receipt.update(claim["receipt_contract"])  # type: ignore[arg-type]
        (destination / "attempt-receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        return destination

    def expire_claim(self, claim: dict[str, object]) -> None:
        state = self.state()
        state["jobs"][claim["job_id"]]["lease_expires_epoch_seconds"] = 0.0  # type: ignore[index]
        self.write_state(state)

    def test_plan_rejects_empty_results_root(self) -> None:
        plan_path = self.write_plan([1])
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["results_root"] = ""
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaisesRegex(POOL.PoolError, "missing results_root"):
            POOL.initialize_pool(self.pool_root, plan_path)

    def test_heterogeneous_lpt_eft_assignment_is_deterministic(self) -> None:
        self.initialize([100, 80, 30, 20])
        state = self.state()
        assignment = POOL.schedule_pending(state, 1000.0, ["gpu0", "gpu1"])
        self.assertEqual(assignment, {"gpu0": ["job1", "job3", "job4"], "gpu1": ["job2"]})
        self.assertEqual(
            POOL.schedule_pending(state, 1000.0, ["gpu0", "gpu1"]),
            assignment,
        )

    def test_offline_worker_does_not_reserve_pending_work(self) -> None:
        self.initialize([100, 80])
        first = POOL.claim_job(self.pool_root, "gpu0")
        self.assertIsNotNone(first)
        self.assertEqual(first["job_id"], "job1")  # type: ignore[index]

    def test_simultaneous_workers_claim_distinct_jobs(self) -> None:
        self.initialize([100, 80, 30])
        first = POOL.claim_job(self.pool_root, "gpu0")
        second = POOL.claim_job(self.pool_root, "gpu1")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first["job_id"], second["job_id"])  # type: ignore[index]

    def test_heartbeat_extends_current_lease(self) -> None:
        self.initialize([10])
        claim = POOL.claim_job(self.pool_root, "gpu0")
        before = self.state()["jobs"]["job1"]["lease_expires_epoch_seconds"]  # type: ignore[index]
        time.sleep(0.01)
        self.assertTrue(POOL.heartbeat(self.pool_root, "gpu0", "job1", claim["lease_epoch"]))  # type: ignore[index]
        after = self.state()["jobs"]["job1"]["lease_expires_epoch_seconds"]  # type: ignore[index]
        self.assertGreater(after, before)

    def test_expired_lease_requeues_with_incremented_epoch(self) -> None:
        self.initialize([10])
        stale = POOL.claim_job(self.pool_root, "gpu0")
        self.expire_claim(stale)
        current = POOL.claim_job(self.pool_root, "gpu1")
        self.assertEqual(current["job_id"], stale["job_id"])  # type: ignore[index]
        self.assertEqual(current["lease_epoch"], stale["lease_epoch"] + 1)  # type: ignore[index]
        self.assertEqual(self.state()["jobs"]["job1"]["attempt_count"], 2)  # type: ignore[index]

    def test_stale_epoch_completion_is_rejected(self) -> None:
        self.initialize([10])
        stale = POOL.claim_job(self.pool_root, "gpu0")
        self.write_publish(stale)
        self.expire_claim(stale)
        current = POOL.claim_job(self.pool_root, "gpu1")
        self.assertIsNotNone(current)
        with self.assertRaisesRegex(POOL.PoolError, "worker is fenced"):
            POOL.complete_job(self.pool_root, "gpu0", "job1", stale["lease_epoch"])

    def test_valid_completion_is_atomic_and_idempotent(self) -> None:
        self.initialize([10])
        claim = POOL.claim_job(self.pool_root, "gpu0")
        publish = self.write_publish(claim)
        completed = POOL.complete_job(self.pool_root, "gpu0", "job1", claim["lease_epoch"])
        self.assertFalse(publish.exists())
        self.assertTrue((completed / "result-TFOsorted").is_file())
        self.assertEqual(self.state()["jobs"]["job1"]["status"], "complete")  # type: ignore[index]
        self.assertEqual(
            POOL.complete_job(self.pool_root, "gpu0", "job1", claim["lease_epoch"]),
            completed,
        )

    def test_bad_artifact_digest_fails_closed(self) -> None:
        self.initialize([10])
        claim = POOL.claim_job(self.pool_root, "gpu0")
        publish = self.write_publish(claim)
        (publish / "result-TFOsorted").write_bytes(b"tampered\n")
        with self.assertRaisesRegex(POOL.PoolError, "artifact (size|digest) mismatch"):
            POOL.complete_job(self.pool_root, "gpu0", "job1", claim["lease_epoch"])
        self.assertEqual(self.state()["jobs"]["job1"]["status"], "leased")  # type: ignore[index]

    def test_conflicting_publications_fail_closed(self) -> None:
        self.initialize([10])
        claim = POOL.claim_job(self.pool_root, "gpu0")
        self.write_publish(claim, b"attempt\n")
        completed = self.results_root / "job1" / "completed"
        self.write_publish(claim, b"different\n", destination=completed)
        with self.assertRaisesRegex(POOL.PoolError, "both attempt and completed"):
            POOL.complete_job(self.pool_root, "gpu0", "job1", claim["lease_epoch"])

    def test_publication_is_recovered_after_rename_before_state_save(self) -> None:
        self.initialize([10])
        claim = POOL.claim_job(self.pool_root, "gpu0")
        publish = self.write_publish(claim)
        completed = self.results_root / "job1" / "completed"
        completed.parent.mkdir(parents=True)
        os.replace(publish, completed)
        summary = POOL.pool_summary(self.pool_root)
        self.assertEqual(summary["job_counts"], {"complete": 1})
        self.assertEqual(self.state()["jobs"]["job1"]["completed_lease_epoch"], 1)  # type: ignore[index]

    def test_restart_preserves_current_claim(self) -> None:
        plan = self.initialize([10])
        first = POOL.claim_job(self.pool_root, "gpu0")
        POOL.initialize_pool(self.pool_root, plan)
        resumed = POOL.claim_job(self.pool_root, "gpu0")
        self.assertEqual(resumed["lease_epoch"], first["lease_epoch"])
        self.assertEqual(resumed["job_id"], first["job_id"])

    def test_max_attempt_failure_is_terminal(self) -> None:
        self.initialize([10], max_attempts=1)
        claim = POOL.claim_job(self.pool_root, "gpu0")
        status = POOL.fail_job(
            self.pool_root, "gpu0", "job1", claim["lease_epoch"], "mock failure"
        )
        self.assertEqual(status, "failed")
        self.assertIsNone(POOL.claim_job(self.pool_root, "gpu1"))
        self.assertEqual(self.state()["jobs"]["job1"]["failure"], "mock failure")  # type: ignore[index]

    def test_expiry_at_attempt_limit_is_terminal(self) -> None:
        self.initialize([10], max_attempts=1)
        claim = POOL.claim_job(self.pool_root, "gpu0")
        self.expire_claim(claim)
        summary = POOL.pool_summary(self.pool_root)
        self.assertEqual(summary["job_counts"], {"failed": 1})

    def test_two_mock_workers_complete_each_job_once(self) -> None:
        mock_runner = self.base / "mock_runner.py"
        mock_runner.write_text(
            """#!/usr/bin/env python3
import hashlib, json, os, pathlib, sys, time
claim = json.loads(pathlib.Path(sys.argv[1]).read_text())
attempt = pathlib.Path(sys.argv[2])
temporary = attempt / 'publish.tmp'
temporary.mkdir()
time.sleep(0.04)
payload = (claim['job_id'] + '\\n').encode()
artifact = temporary / 'result-TFOsorted'
artifact.write_bytes(payload)
receipt = {
    'schema_version': 'long_query_dynamic_gpu_attempt_receipt_v1',
    'status': 'complete',
    'pool_id': claim['pool_id'],
    'job_id': claim['job_id'],
    'gene_id': claim['gene_id'],
    'worker_id': claim['worker_id'],
    'lease_epoch': claim['lease_epoch'],
    'query_file_sha256': claim['row']['query_file_sha256'],
    'query_sequence_sha256': claim['row']['query_sequence_sha256'],
    'artifact_path': artifact.name,
    'artifact_size_bytes': len(payload),
    'artifact_sha256': hashlib.sha256(payload).hexdigest(),
    'wall_seconds': 0.04,
}
receipt.update(claim['receipt_contract'])
(temporary / 'attempt-receipt.json').write_text(json.dumps(receipt))
os.replace(temporary, attempt / 'publish')
""",
            encoding="utf-8",
        )
        self.initialize(
            [100, 90, 80, 70, 60, 50, 40, 30],
            runner_command=[
                sys.executable,
                str(mock_runner),
                "{claim_json}",
                "{attempt_dir}",
            ],
        )
        command = [sys.executable, str(SCRIPT), "run-worker", "--root", str(self.pool_root)]
        workers = [
            subprocess.Popen(command + ["--worker-id", worker_id])
            for worker_id in ("gpu0", "gpu1")
        ]
        return_codes = [worker.wait(timeout=20) for worker in workers]
        self.assertEqual(return_codes, [0, 0])
        self.assertEqual(POOL.pool_summary(self.pool_root)["job_counts"], {"complete": 8})
        for index in range(1, 9):
            artifact = self.results_root / f"job{index}" / "completed" / "result-TFOsorted"
            self.assertEqual(artifact.read_text(encoding="ascii"), f"job{index}\n")
        events = (self.pool_root / "events.tsv").read_text(encoding="utf-8")
        self.assertEqual(events.count("\tjob_completed\t"), 8)


if __name__ == "__main__":
    unittest.main()
