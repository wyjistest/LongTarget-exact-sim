#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARIZER = ROOT / "scripts" / "summarize_fasim_gasal2_traceback_certificate.py"
PREFIX = "benchmark.fasim_gasal2_traceback_certificate_shadow_"


def telemetry(considered: int, certified: int, false_rejects: int = 0) -> str:
    values: dict[str, str | int | float] = {
        "requested": 1,
        "active": 1,
        "real_skip_enabled": 0,
        "pre_drop_proof_available": 1,
        "proof_version": "phase6_exact_v1",
        "candidates_considered": considered,
        "certified_skips": certified,
        "uncertified_candidates": considered - certified,
        "exact_descriptor_duplicate_skips": 0,
        "static_span_skips": 0,
        "score_endpoint_span_skips": certified,
        "shadow_false_rejects": false_rejects,
        "score_frontier_skips": 0,
        "stability_frontier_skips": 0,
        "nt_frontier_skips": 0,
        "tie_rescues": 0,
        "rank_aware_supported": 0,
        "probe_requests": considered,
        "probe_seconds": 1.25,
        "fallbacks": 0,
    }
    values["authority_traceback_requests"] = considered
    lines = [f"{PREFIX}{key}={value}" for key, value in values.items()]
    lines.extend(
        [
            f"benchmark.fasim_gasal2_traceback_requests={considered}",
            "benchmark.fasim_gasal2_fallbacks=0",
            "benchmark.fasim_gasal2_length_guard_fallbacks=0",
        ]
    )
    return "\n".join(lines) + "\n"


class TracebackCertificateSummarizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_summarizer(
        self, logs: list[Path], output: Path
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "python3",
            str(SUMMARIZER),
            "--workload",
            "fixture",
            "--query",
            "query.fa",
            "--target",
            "target.fa",
            "--scope",
            "fixture_scope",
            "--output-contract",
            "byte_equal",
            "--output",
            str(output),
        ]
        for log in logs:
            command.extend(["--stderr", str(log)])
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def test_sums_logs_and_marks_subthreshold_candidate_no_go(self) -> None:
        first = self.root / "first.log"
        second = self.root / "second.log"
        first.write_text(telemetry(100, 10), encoding="utf-8")
        second.write_text(telemetry(200, 20), encoding="utf-8")
        output = self.root / "row.tsv"

        result = self.run_summarizer([first, second], output)

        self.assertEqual(result.returncode, 0, result.stderr)
        with output.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["logs"], "2")
        self.assertEqual(row["candidates_considered"], "300")
        self.assertEqual(row["certified_skips"], "30")
        self.assertEqual(row["certified_fraction"], "0.100000")
        self.assertEqual(row["score_endpoint_span_skips"], "30")
        self.assertEqual(row["shadow_false_rejects"], "0")
        self.assertEqual(row["decision"], "no_go_below_request_reduction_gate")

    def test_marks_material_shadow_as_requiring_runtime_gate(self) -> None:
        log = self.root / "material.log"
        log.write_text(telemetry(100, 25), encoding="utf-8")
        output = self.root / "row.tsv"

        result = self.run_summarizer([log], output)

        self.assertEqual(result.returncode, 0, result.stderr)
        with output.open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(row["decision"], "shadow_material_requires_runtime_gate")

    def test_fails_closed_on_false_reject(self) -> None:
        log = self.root / "bad.log"
        log.write_text(telemetry(100, 25, false_rejects=1), encoding="utf-8")

        result = self.run_summarizer([log], self.root / "row.tsv")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("shadow_false_rejects must be zero", result.stderr)


if __name__ == "__main__":
    unittest.main()
