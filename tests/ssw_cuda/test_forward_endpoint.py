#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DRIVER = ROOT / ".paper-artifacts/ssw-cuda-v1/forward/build/ssw_cuda_forward_driver"
DEFAULT_STUB = ROOT / ".paper-artifacts/ssw-cuda-v1/preselect/build/ssw_cuda_stub_probe"
DRIVER = Path(os.environ.get("SSW_CUDA_PHASE6_DRIVER", DEFAULT_DRIVER)).resolve()
STUB = Path(os.environ.get("SSW_CUDA_PHASE6_STUB_PROBE", DEFAULT_STUB)).resolve()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_module("ssw_cuda_phase6_runner", ROOT / "reproduce/ssw_cuda/run_phase6_forward.py")


def run(command: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env={
            **os.environ,
            "CUDA_VISIBLE_DEVICES": "0,1",
            "FASIM_TRANSFERSTRING_TABLE": "0",
            "FASIM_SSW_ORACLE_TRACE": "0",
        },
    )


def run_cases(cases: list[object]) -> tuple[subprocess.CompletedProcess[str], list[dict[str, str]]]:
    with tempfile.TemporaryDirectory(prefix="ssw-cuda-p6-test-") as directory:
        input_path = Path(directory) / "input.tsv"
        input_path.write_bytes(RUNNER.input_tsv(cases))
        completed = run([str(DRIVER), "--input", str(input_path), "--device", "0"])
    rows = (
        list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
        if completed.stdout.startswith("case_id\t")
        else []
    )
    return completed, rows


class Phase6ForwardEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not DRIVER.is_file() or not STUB.is_file():
            raise RuntimeError("Phase 6 driver and stub probe must be built before tests")

    def test_frozen_case_and_attempt_counts(self) -> None:
        groups, endpoints = RUNNER.case_groups()
        self.assertEqual(
            {name: len(values) for name, values in groups.items()},
            {
                "tiny_exhaustive": 196,
                "adversarial_compact": 30,
                "compact_fuzz": 128,
                "known_forward": 4,
                "large": 267,
                "determinism": 18,
                "unsupported": 4,
            },
        )
        self.assertEqual(set(endpoints), {
            "known-hq10-ht02-forward-call",
            "known-hq11-ht02-forward-call",
        })
        plan = RUNNER.validate_plan()
        self.assertEqual(len(plan), 31)
        self.assertEqual(
            sum(
                int(row["unique_case_count"])
                for row in plan
                if row["execution_stage"] in {"primary", "determinism", "same_model_dual_gpu"}
            ),
            841,
        )

    def test_production_source_has_full_gpu_endpoint_without_case_specialization(self) -> None:
        forward = (ROOT / "fasim/ssw_cuda/ssw_cuda_forward.cu").read_text(encoding="utf-8")
        striped = (ROOT / "fasim/ssw_cuda/ssw_cuda_striped.cuh").read_text(encoding="utf-8")
        combined = forward + striped
        for marker in (
            "full_forward_kernel",
            "column_endpoint_kernel",
            "striped_forward_pass<16, true>",
            "striped_forward_pass<8, false>",
            "result->read_end1 = read_end",
            "if(numeric_path == NUMERIC_PATH_BYTE8) ++right_edge",
        ):
            self.assertIn(marker, combined)
        for forbidden in (
            "hq10",
            "hq11",
            "FAM230I",
            "PXN-AS1",
            "allowlist",
            "blacklist",
            "StripedSmithWaterman",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn(".Align(", combined)

    def test_phase5_smoke_is_exact_at_l3(self) -> None:
        completed = run(
            [str(DRIVER), "--input", "tests/ssw_cuda/fixtures/phase5_smoke.tsv", "--device", "0"]
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + "\n" + completed.stdout)
        rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["column_equal"] == "1" for row in rows))
        self.assertTrue(all(row["reducer_equal"] == "1" for row in rows))
        self.assertTrue(all(row["gpu_equal"] == "1" for row in rows))
        self.assertTrue(all(row["cpu_endpoint_calls"] == "0" for row in rows))

    def test_frozen_hq10_hq11_forward_calls_are_exact(self) -> None:
        cases, expected = RUNNER.endpoint_call_cases()
        completed, rows = run_cases(cases)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(rows), 2)
        by_id = {row["case_id"]: row for row in rows}
        for case_id, endpoint in expected.items():
            row = by_id[case_id]
            self.assertEqual(row["numeric_path"], endpoint.numeric_path)
            for prefix in ("cpu", "gpu"):
                self.assertEqual(int(row[f"{prefix}_score1"]), endpoint.score1)
                self.assertEqual(int(row[f"{prefix}_ref_end1"]), endpoint.ref_end1)
                self.assertEqual(int(row[f"{prefix}_read_end1"]), endpoint.read_end1)
                self.assertEqual(int(row[f"{prefix}_score2"]), endpoint.score2)
                self.assertEqual(int(row[f"{prefix}_ref_end2"]), endpoint.ref_end2)
            self.assertEqual(row["column_equal"], "1")
            self.assertEqual(row["reducer_equal"], "1")
            self.assertEqual(row["gpu_equal"], "1")

    def test_frozen_cpu_forward_vectors_reduce_to_exact_endpoints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssw-cuda-p6-columns-") as directory:
            input_path = Path(directory) / "columns.tsv"
            input_path.write_bytes(RUNNER.frozen_column_input_tsv())
            completed = run(
                [str(DRIVER), "--column-input", str(input_path), "--device", "0"]
            )
        self.assertEqual(completed.returncode, 0, completed.stderr + "\n" + completed.stdout)
        rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["reducer_equal"] == "1" for row in rows))
        self.assertTrue(all(row["cpu_endpoint_calls"] == "0" for row in rows))

    def test_equal_endpoint_and_byte_word_boundaries_are_exact(self) -> None:
        groups, _ = RUNNER.case_groups()
        wanted = {
            "adv-equal-forward",
            "adv-byte-boundary-253",
            "adv-byte-boundary-254",
            "adv-byte-boundary-255",
            "adv-byte-boundary-256",
        }
        cases = [case for case in groups["adversarial_compact"] if case.case_id in wanted]
        self.assertEqual({case.case_id for case in cases}, wanted)
        completed, rows = run_cases(cases)
        self.assertEqual(completed.returncode, 0, completed.stderr + "\n" + completed.stdout)
        self.assertTrue(all(row["reducer_equal"] == row["gpu_equal"] == "1" for row in rows))
        by_id = {row["case_id"]: row for row in rows}
        self.assertEqual(by_id["adv-byte-boundary-253"]["numeric_path"], "word16")
        self.assertEqual(by_id["adv-byte-boundary-254"]["numeric_path"], "word16")
        self.assertEqual(by_id["adv-byte-boundary-255"]["numeric_path"], "word16")
        self.assertEqual(by_id["adv-byte-boundary-256"]["numeric_path"], "word16")
        self.assertTrue(
            all(by_id[case_id]["column_equal"] == "0" for case_id in wanted if case_id != "adv-equal-forward")
        )

    def test_forward_and_reducer_apis_fail_closed(self) -> None:
        for probe in RUNNER.FORWARD_FAIL_PROBES:
            completed = run([str(DRIVER), "--invalid-forward-probe", probe, "--device", "0"])
            self.assertEqual(completed.returncode, 0, f"{probe}: {completed.stderr}")
            self.assertIn("status=", completed.stdout)
            self.assertNotIn("status=ok", completed.stdout)
        for probe in RUNNER.REDUCER_FAIL_PROBES:
            completed = run([str(DRIVER), "--invalid-reducer-probe", probe, "--device", "0"])
            self.assertEqual(completed.returncode, 0, f"{probe}: {completed.stderr}")
            self.assertIn("status=", completed.stdout)
            self.assertNotIn("status=ok", completed.stdout)

    def test_non_cuda_stub_fails_closed_for_forward_apis(self) -> None:
        completed = run([str(STUB)])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "ssw_cuda_stub_status=not_built")

    def test_default_fasim_target_does_not_link_phase6_backend(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        sources_line = next(line for line in makefile.splitlines() if line.startswith("FASIM_SOURCES :="))
        self.assertNotIn("ssw_cuda", sources_line)
        build_rule = makefile[makefile.index("$(FASIM_TARGET):"):makefile.index(".PHONY: build-ssw-cuda-phase1-profile")]
        self.assertNotIn("fasim/ssw_cuda", build_rule)


if __name__ == "__main__":
    unittest.main()
