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
DEFAULT_DRIVER = (
    ROOT
    / ".paper-artifacts/ssw-cuda-v1/forward-hybrid/build/ssw_cpu_continuation_driver"
)
DRIVER = Path(os.environ.get("SSW_CUDA_PHASE7_CONTINUATION_DRIVER", DEFAULT_DRIVER)).resolve()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P6 = load_module("ssw_cuda_phase7_phase6", ROOT / "reproduce/ssw_cuda/run_phase6_forward.py")


def run(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
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
            "FASIM_SSW_AVX2": "0",
            "FASIM_SSW_PROFILE_CACHE": "0",
            "FASIM_SSW_PROFILE_CONTEXT": "0",
            "FASIM_SSW_ORACLE_TRACE": "0",
            "FASIM_TRANSFERSTRING_TABLE": "0",
        },
    )


def run_cases(
    cases: list[object], *, hybrid: bool = False
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, str]]]:
    with tempfile.TemporaryDirectory(prefix="ssw-cuda-p7-continuation-") as directory:
        input_path = Path(directory) / "input.tsv"
        input_path.write_bytes(P6.input_tsv(cases))
        command = [str(DRIVER), "--input", str(input_path), "--device", "0"]
        if hybrid:
            command.insert(1, "--hybrid")
        completed = run(command)
    rows = (
        list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
        if completed.stdout.startswith("case_id\t")
        else []
    )
    return completed, rows


class CpuContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not DRIVER.is_file():
            raise RuntimeError("Phase 7 continuation driver must be built before tests")

    def test_entire_frozen_primary_corpus_is_exact(self) -> None:
        groups, _ = P6.case_groups()
        cases = (
            groups["tiny_exhaustive"]
            + groups["adversarial_compact"]
            + groups["compact_fuzz"]
            + groups["known_forward"]
            + groups["large"]
        )
        self.assertEqual(len(cases), 625)
        completed, rows = run_cases(cases)
        self.assertEqual(completed.returncode, 0, completed.stderr + "\n" + completed.stdout)
        self.assertEqual(len(rows), 625)
        self.assertTrue(all(row["raw_equal"] == "1" for row in rows))
        self.assertTrue(all(row["wrapper_equal"] == "1" for row in rows))
        self.assertTrue(all(row["cpu_forward_calls"] == "0" for row in rows))
        self.assertTrue(all(row["gpu_cpu_endpoint_calls"] == "0" for row in rows))
        self.assertEqual(sum(row["numeric_path"] == "word16" for row in rows), 34)
        self.assertEqual(sum(row["authority_score1"] == "0" for row in rows), 18)
        for row in rows:
            expected = "0" if row["authority_score1"] == "0" else "1"
            self.assertEqual(row["cpu_reverse_calls"], expected, row["case_id"])
            self.assertEqual(row["cpu_banded_sw_calls"], expected, row["case_id"])

    def test_hq10_hq11_reverse_start_and_cigar_are_exact(self) -> None:
        cases, _ = P6.endpoint_call_cases()
        completed, rows = run_cases(cases)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        by_id = {row["case_id"]: row for row in rows}
        expected = {
            "known-hq10-ht02-forward-call": ("12", "1696", "20M1I4M2D31M"),
            "known-hq11-ht02-forward-call": ("22", "725", "18M4I44M"),
        }
        self.assertEqual(set(by_id), set(expected))
        for case_id, (ref_begin, read_begin, cigar) in expected.items():
            row = by_id[case_id]
            self.assertEqual(row["continuation_ref_begin1"], ref_begin)
            self.assertEqual(row["continuation_read_begin1"], read_begin)
            self.assertEqual(row["continuation_cigar"], cigar)
            self.assertEqual(row["raw_equal"], row["wrapper_equal"])
            self.assertEqual(row["wrapper_equal"], "1")

    def test_gpu_l1_l2_l3_attempt_selection_matches_cpu(self) -> None:
        groups, _ = P6.case_groups()
        cases = (
            groups["tiny_exhaustive"]
            + groups["adversarial_compact"]
            + groups["compact_fuzz"]
            + groups["known_forward"]
            + groups["large"]
        )
        completed, rows = run_cases(cases, hybrid=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + "\n" + completed.stdout)
        self.assertEqual(len(rows), 549)
        for row in rows:
            self.assertEqual(row["cpu_selected"], row["gpu_selected"], row["case_id"])
            self.assertEqual(row["cpu_start"], row["gpu_start"], row["case_id"])
            self.assertEqual(row["cpu_cutlength"], row["gpu_cutlength"], row["case_id"])
            self.assertEqual(row["cpu_reason"], row["gpu_reason"], row["case_id"])
            self.assertEqual(row["endpoint_equal"], "1", row["case_id"])
            self.assertEqual(row["continuation_equal"], "1", row["case_id"])
            self.assertEqual(row["cpu_forward_calls"], "0", row["case_id"])
            self.assertEqual(row["cpu_reverse_calls"], "1", row["case_id"])
            self.assertEqual(row["cpu_banded_sw_calls"], "1", row["case_id"])

    def test_invalid_forward_tuples_fail_closed(self) -> None:
        probes = (
            "null_profile",
            "null_reference",
            "null_endpoint",
            "bad_ref_end",
            "bad_read_end",
            "bad_second_end",
            "bad_numeric_path",
            "empty_reference",
        )
        for probe in probes:
            completed = run([str(DRIVER), "--invalid-probe", probe])
            self.assertEqual(completed.returncode, 0, f"{probe}: {completed.stderr}")
            self.assertEqual(completed.stdout.strip(), f"probe={probe} rejected=1")

    def test_continuation_sources_have_no_case_specialization_or_forward_call(self) -> None:
        core = (ROOT / "fasim/sswNew.cpp").read_text(encoding="utf-8")
        wrapper = (ROOT / "fasim/ssw_cpp.cpp").read_text(encoding="utf-8")
        core_body = core[core.index("s_align* ssw_align_from_forward"):core.index("void align_destroy")]
        wrapper_body = wrapper[
            wrapper.index("bool Aligner::AlignFromForward"):wrapper.index("void Aligner::Clear")
        ]
        for forbidden in ("hq10", "hq11", "FAM230I", "PXN-AS1", "allowlist", "blacklist"):
            self.assertNotIn(forbidden, core_body + wrapper_body)
        self.assertNotIn("ssw_align(", core_body)
        self.assertNotIn("ssw_align(", wrapper_body.replace("ssw_align_from_forward(", ""))
        self.assertIn("ssw_align_from_forward(", wrapper_body)


if __name__ == "__main__":
    unittest.main()
