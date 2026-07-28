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
DEFAULT_DRIVER = ROOT / ".paper-artifacts/ssw-cuda-v1/preselect/build/ssw_cuda_preselect_driver"
DEFAULT_STUB = ROOT / ".paper-artifacts/ssw-cuda-v1/preselect/build/ssw_cuda_stub_probe"
DRIVER = Path(os.environ.get("SSW_CUDA_PHASE5_DRIVER", DEFAULT_DRIVER)).resolve()
STUB = Path(os.environ.get("SSW_CUDA_PHASE5_STUB_PROBE", DEFAULT_STUB)).resolve()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_module("ssw_cuda_phase5_runner", ROOT / "reproduce/ssw_cuda/run_phase5_preselect.py")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )


class Phase5PreselectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not DRIVER.is_file() or not STUB.is_file():
            raise RuntimeError("Phase 5 driver and stub probe must be built before tests")

    def test_frozen_case_and_attempt_counts(self) -> None:
        cases = RUNNER.all_cases()
        groups = RUNNER.case_groups(cases)
        self.assertEqual(len(cases), 627)
        self.assertEqual(len(groups["tiny_exhaustive"]), 196)
        self.assertEqual(len(groups["adversarial_compact"]), 30)
        self.assertEqual(len(groups["compact_fuzz"]), 128)
        self.assertEqual(len(groups["known_hq10_hq11"]), 2)
        self.assertEqual(len(groups["large"]), 267)
        self.assertEqual(len(groups["unsupported"]), 4)
        self.assertEqual(len(groups["determinism"]), 16)
        plan = RUNNER.validate_plan()
        self.assertEqual(len(plan), 29)
        self.assertEqual(
            sum(
                int(row["unique_case_count"])
                for row in plan
                if row["execution_stage"] in {"primary", "determinism", "same_model_dual_gpu"}
            ),
            815,
        )

    def test_production_source_has_exact_stable_structure_without_case_ids(self) -> None:
        prealign = (ROOT / "fasim/ssw_cuda/ssw_cuda_pre_align.cu").read_text(encoding="utf-8")
        select = (ROOT / "fasim/ssw_cuda/ssw_cuda_select.cu").read_text(encoding="utf-8")
        for marker in (
            "striped_prealign_pass<16, true>",
            "striped_prealign_pass<8, false>",
            "kContractGapOpen",
            "kContractGapExtend",
            "static_cast<int8_t>",
        ):
            self.assertIn(marker, prealign)
        for marker in (
            "selection_flag_kernel",
            "selection_scan_kernel",
            "selection_scatter_kernel",
            "ATTEMPT_BEST_FALLBACK",
            "ATTEMPT_LAST",
        ):
            self.assertIn(marker, select)
        for forbidden in ("hq10", "hq11", "FAM230I", "PXN-AS1", "allowlist", "blacklist"):
            self.assertNotIn(forbidden, prealign + select)

    def test_smoke_l1_l2_exact(self) -> None:
        completed = run(
            [str(DRIVER), "--input", "tests/ssw_cuda/fixtures/phase5_smoke.tsv", "--device", "0"]
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["column_equal"] == "1" for row in rows))
        self.assertTrue(all(row["scoreinfo_equal"] == "1" for row in rows))

    def test_known_hq_calls_match_frozen_cpu_fixtures(self) -> None:
        cases = RUNNER.case_groups(RUNNER.all_cases())["known_hq10_hq11"]
        with tempfile.TemporaryDirectory(prefix="ssw-cuda-p5-known-") as directory:
            path = Path(directory) / "known.tsv"
            path.write_bytes(RUNNER.input_tsv(cases))
            completed = run([str(DRIVER), "--input", str(path), "--device", "0"])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rows = {row["case_id"]: row for row in csv.DictReader(io.StringIO(completed.stdout), delimiter="\t")}
        self.assertEqual(rows["known-hq10-ht02-traceback"]["cpu_column_digest"], "4cdb83f5d1b579b4")
        self.assertEqual(rows["known-hq11-ht02-endpoint"]["cpu_column_digest"], "fcd5135e90526dfa")
        self.assertTrue(all(row["column_equal"] == "1" and row["scoreinfo_equal"] == "1" for row in rows.values()))

    def test_attempt_selection_reasons_are_stable(self) -> None:
        completed = run([str(DRIVER), "--attempt-probe"])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
        selected = {
            (row["scoreinfo_index"], row["attempt_order"]): row["reason"]
            for row in rows
            if row["selected"] == "1"
        }
        self.assertEqual(
            selected,
            {("0", "1"): "threshold", ("1", "1"): "best_fallback", ("2", "2"): "last"},
        )
        self.assertFalse(any(row["selected"] == "1" for row in rows if row["scoreinfo_index"] == "3"))

    def test_invalid_inputs_and_non_cuda_stub_fail_closed(self) -> None:
        for probe in RUNNER.EXTRA_FAIL_PROBES:
            completed = run([str(DRIVER), "--invalid-probe", probe, "--device", "0"])
            self.assertEqual(completed.returncode, 0, f"{probe}: {completed.stderr}")
            self.assertIn("status=", completed.stdout)
            self.assertNotIn("status=ok", completed.stdout)
        stub = run([str(STUB)])
        self.assertEqual(stub.returncode, 0, stub.stderr)
        self.assertEqual(stub.stdout.strip(), "ssw_cuda_stub_status=not_built")

    def test_default_fasim_target_does_not_link_phase5_backend(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        sources_line = next(line for line in makefile.splitlines() if line.startswith("FASIM_SOURCES :="))
        self.assertNotIn("ssw_cuda", sources_line)
        build_rule = makefile[makefile.index("$(FASIM_TARGET):"):makefile.index(".PHONY: build-ssw-cuda-phase1-profile")]
        self.assertNotIn("fasim/ssw_cuda", build_rule)


if __name__ == "__main__":
    unittest.main()
