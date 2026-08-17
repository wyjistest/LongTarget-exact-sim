#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CPU_BINARY = ROOT / "fasim_longtarget_x86"
F_BINARY = (
    ROOT / ".paper-artifacts/ssw-cuda-v1/forward-hybrid/build/fasim_forward_hybrid"
)
TARGET = (
    ROOT
    / "reproduce/bioinformatics/holdout_inputs/targets/"
    "ht02_ENSG00000198722_chr9_35159829_35162329.fa"
)
CASES = (
    (
        "hq10",
        ROOT
        / "reproduce/bioinformatics/holdout_inputs/queries/"
        "hq10_ENSG00000178248_ENST00000785836.fa",
        "c34ff3fbdb9d1a069397615e2ed695dd336eb2055ce389a8ccade83e3858cb88",
    ),
    (
        "hq11",
        ROOT
        / "reproduce/bioinformatics/holdout_inputs/queries/"
        "hq11_ENSG00000255857_ENST00000667017.fa",
        "394fe813c2e10d9340165d371255a8a54bf493e3c9da90d57db4e99dfd72cd82",
    ),
)


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command(binary: Path, query: Path, output: Path) -> list[str]:
    return [
        str(binary),
        "-f1",
        str(TARGET),
        "-f2",
        str(query),
        "-r",
        "0",
        "-cn",
        "1",
        "-O",
        str(output),
    ]


def environment(**updates: str) -> dict[str, str]:
    value = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "0,1",
        "FASIM_OUTPUT_MODE": "tfosorted",
        "FASIM_SSW_AVX2": "0",
        "FASIM_SSW_PROFILE_CACHE": "0",
        "FASIM_SSW_PROFILE_CONTEXT": "0",
        "FASIM_SSW_ORACLE_TRACE": "0",
        "FASIM_TRANSFERSTRING_TABLE": "0",
    }
    value.update(updates)
    return value


def run(binary: Path, query: Path, output: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    output.mkdir()
    return subprocess.run(
        command(binary, query, output),
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )


def only_output(directory: Path) -> Path:
    files = [path for path in directory.iterdir() if path.is_file()]
    if len(files) != 1:
        raise AssertionError(f"expected one output in {directory}, got {files}")
    return files[0]


class ForwardHybridRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (CPU_BINARY, F_BINARY, TARGET):
            if not path.is_file():
                raise RuntimeError(f"required runtime dependency is missing: {path}")

    def test_hq10_hq11_outputs_and_cpu_call_contract_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssw-forward-hybrid-runtime-") as directory:
            root = Path(directory)
            for case_id, query, expected_digest in CASES:
                cpu_dir = root / f"{case_id}-cpu"
                f_dir = root / f"{case_id}-f"
                telemetry = root / f"{case_id}-f.tsv"
                cpu = run(
                    CPU_BINARY,
                    query,
                    cpu_dir,
                    environment(FASIM_SSW_BACKEND="cpu"),
                )
                hybrid = run(
                    F_BINARY,
                    query,
                    f_dir,
                    environment(
                        FASIM_SSW_BACKEND="cuda-forward-hybrid",
                        FASIM_SSW_FORWARD_HYBRID_TELEMETRY_PATH=str(telemetry),
                        FASIM_SSW_CUDA_DEVICE="0",
                        FASIM_SSW_FORWARD_HYBRID_MAX_TASKS="16",
                    ),
                )
                self.assertEqual(cpu.returncode, 0, cpu.stderr)
                self.assertEqual(hybrid.returncode, 0, hybrid.stderr)
                cpu_output = only_output(cpu_dir)
                hybrid_output = only_output(f_dir)
                self.assertEqual(cpu_output.read_bytes(), hybrid_output.read_bytes())
                self.assertEqual(sha256(cpu_output), expected_digest)
                with telemetry.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle, delimiter="\t"))
                self.assertEqual(len(rows), 1)
                row = rows[0]
                self.assertEqual(row["status"], "complete")
                self.assertEqual(row["cpu_prealign_calls"], "0")
                self.assertEqual(row["cpu_forward_calls"], "0")
                self.assertEqual(row["fallback_calls"], "0")
                self.assertEqual(row["cpu_failures"], "0")
                self.assertEqual(row["selected"], row["cpu_continuation_calls"])
                self.assertEqual(row["cpu_reverse_calls"], row["cpu_continuation_calls"])
                self.assertEqual(row["cpu_banded_sw_calls"], row["cpu_continuation_calls"])
                for field in (
                    "gpu_packing_seconds",
                    "gpu_h2d_seconds",
                    "gpu_prealign_kernel_seconds",
                    "gpu_selection_kernel_seconds",
                    "gpu_forward_kernel_seconds",
                    "gpu_endpoint_reduce_seconds",
                    "gpu_d2h_seconds",
                    "gpu_unattributed_overhead_seconds",
                    "cpu_reverse_start_seconds",
                    "cpu_banded_traceback_seconds",
                    "cpu_cigar_seconds",
                    "downstream_conversion_seconds",
                    "cluster_sort_seconds",
                    "filter_seconds",
                ):
                    self.assertGreaterEqual(float(row[field]), 0.0, field)
                self.assertGreater(float(row["gpu_prealign_kernel_seconds"]), 0.0)
                self.assertGreater(float(row["gpu_forward_kernel_seconds"]), 0.0)
                self.assertGreater(float(row["cpu_reverse_start_seconds"]), 0.0)
                self.assertGreater(float(row["cpu_banded_traceback_seconds"]), 0.0)
                self.assertGreater(int(row["device_workspace_peak_bytes"]), 0)

    def test_default_binary_and_telemetry_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ssw-forward-hybrid-fail-") as directory:
            root = Path(directory)
            query = CASES[0][1]
            default = run(
                CPU_BINARY,
                query,
                root / "default",
                environment(FASIM_SSW_BACKEND="cuda-forward-hybrid"),
            )
            self.assertEqual(default.returncode, 2)
            self.assertIn("backend is not built", default.stderr)

            missing = run(
                F_BINARY,
                query,
                root / "missing",
                environment(FASIM_SSW_BACKEND="cuda-forward-hybrid"),
            )
            self.assertEqual(missing.returncode, 2)
            self.assertIn("requires a new telemetry path", missing.stderr)

            existing_telemetry = root / "existing.tsv"
            existing_telemetry.write_text("do not overwrite\n", encoding="utf-8")
            existing = run(
                F_BINARY,
                query,
                root / "existing",
                environment(
                    FASIM_SSW_BACKEND="cuda-forward-hybrid",
                    FASIM_SSW_FORWARD_HYBRID_TELEMETRY_PATH=str(existing_telemetry),
                ),
            )
            self.assertEqual(existing.returncode, 2)
            self.assertEqual(existing_telemetry.read_text(encoding="utf-8"), "do not overwrite\n")

    def test_default_build_does_not_link_forward_hybrid(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        sources_line = next(line for line in makefile.splitlines() if line.startswith("FASIM_SOURCES :="))
        self.assertNotIn("ssw_cuda_forward_hybrid", sources_line)
        self.assertIn("-DFASIM_WITH_SSW_CUDA_FORWARD_HYBRID", makefile)


if __name__ == "__main__":
    unittest.main()
