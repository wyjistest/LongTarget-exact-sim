#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "run_long_query_dynamic_f1_attempt.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DynamicF1AttemptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="longtarget-attempt-test-")
        self.base = Path(self.temporary.name)
        self.attempt = self.base / "attempt"
        self.attempt.mkdir()
        self.query = self.base / "query.fa"
        self.query.write_text(">q\nACGTACGT\n", encoding="ascii")
        self.target = self.base / "target.fa"
        self.target.write_text(">t\nACGTACGTACGT\n", encoding="ascii")
        self.binary = self.base / "mock_fasim.py"
        self.binary.write_text(
            """#!/usr/bin/env python3
import os, pathlib, sys
output = pathlib.Path(sys.argv[sys.argv.index('-O') + 1])
output.mkdir(parents=True, exist_ok=True)
(output / 'mock-TFOsorted').write_text('byte-identical-output\\n')
pathlib.Path(os.environ['FASIM_LONG_QUERY_GPU_CONSUMER_F1_REPORT']).write_text('field\\tvalue\\n')
print('finished normally')
markers = [
 'benchmark.fasim_long_query_gpu_consumer_f1_pipeline_active=1',
 'benchmark.fasim_long_query_gpu_consumer_f1_pipeline_failures=0',
 'benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches=0',
 'benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks=0',
 'benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0',
 'benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_fallbacks=0',
]
if os.environ.get('MOCK_MISSING_MARKER') == '1':
    markers.pop()
for marker in markers:
    print(marker, file=sys.stderr)
""",
            encoding="utf-8",
        )
        self.binary.chmod(0o755)
        cpu = min(os.sched_getaffinity(0))
        self.contract = {
            "source_commit": "a438ccf-test",
            "binary_sha256": sha256(self.binary),
            "target_sha256": sha256(self.target),
            "execution_mode": "consumer_driven_f1_exact_pipeline",
        }
        self.claim = {
            "schema_version": "long_query_dynamic_gpu_pool_claim_v1",
            "pool_id": "test-pool",
            "job_id": "job1",
            "gene_id": "ENSG00000000001",
            "worker_id": "gpu0",
            "gpu_id": "0",
            "gpu_uuid": "GPU-test",
            "cpu_affinity": str(cpu),
            "lease_epoch": 1,
            "row": {
                "query_path": str(self.query),
                "query_length_nt": "8",
                "query_file_sha256": sha256(self.query),
                "query_sequence_sha256": hashlib.sha256(b"ACGTACGT").hexdigest(),
            },
            "receipt_contract": self.contract,
        }
        self.claim_path = self.attempt / "claim.json"
        self.claim_path.write_text(json.dumps(self.claim), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "LONGTARGET_POOL_ID": self.claim["pool_id"],
                "LONGTARGET_POOL_JOB_ID": self.claim["job_id"],
                "LONGTARGET_POOL_WORKER_ID": self.claim["worker_id"],
                "LONGTARGET_POOL_LEASE_EPOCH": str(self.claim["lease_epoch"]),
                "LONGTARGET_F1_BINARY": str(self.binary),
                "LONGTARGET_F1_BINARY_SHA256": self.contract["binary_sha256"],
                "LONGTARGET_F1_SOURCE_COMMIT": self.contract["source_commit"],
                "LONGTARGET_F1_TARGET": str(self.target),
                "LONGTARGET_F1_TARGET_SHA256": self.contract["target_sha256"],
                "LONGTARGET_F1_TARGET_LENGTH": "12",
                "LONGTARGET_F1_MIN_QUERY_LENGTH": "1",
                "LONGTARGET_F1_MAX_QUERY_LENGTH": "100",
                "LONGTARGET_F1_VERIFY_GPU_UUID": "0",
            }
        )
        return environment

    def run_adapter(self, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ADAPTER),
                "--claim",
                str(self.claim_path),
                "--attempt-dir",
                str(self.attempt),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )

    def test_success_publishes_exact_artifact_and_receipt(self) -> None:
        completed = self.run_adapter(self.environment())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        publish = self.attempt / "publish"
        receipt = json.loads((publish / "attempt-receipt.json").read_text(encoding="utf-8"))
        artifact = publish / receipt["artifact_path"]
        self.assertEqual(artifact.read_bytes(), b"byte-identical-output\n")
        self.assertEqual(receipt["artifact_sha256"], sha256(artifact))
        self.assertEqual(receipt["lease_epoch"], 1)
        self.assertEqual(receipt["binary_sha256"], self.contract["binary_sha256"])
        self.assertFalse((self.attempt / "work").exists())

    def test_missing_exactness_marker_never_publishes(self) -> None:
        environment = self.environment()
        environment["MOCK_MISSING_MARKER"] = "1"
        completed = self.run_adapter(environment)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("missing required markers", completed.stderr)
        self.assertFalse((self.attempt / "publish").exists())
        self.assertTrue((self.attempt / "failure.json").is_file())

    def test_binary_digest_drift_never_executes(self) -> None:
        environment = self.environment()
        environment["LONGTARGET_F1_BINARY_SHA256"] = "0" * 64
        completed = self.run_adapter(environment)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("binary digest drift", completed.stderr)
        self.assertFalse((self.attempt / "publish").exists())


if __name__ == "__main__":
    unittest.main()
