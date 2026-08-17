#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARE = ROOT / "scripts" / "compare_fasim_gasal2_long_query_integrated.py"
HEADER = (
    "QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
    "StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\tStrand\t"
    "Rule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\tTFO sequence\tTTS sequence\n"
)


def output_text() -> str:
    rows = []
    for index in range(5):
        query_start = index * 100
        query_end = query_start + 59
        target_start = 1000 + index * 100
        target_end = target_start + 59
        rows.append(
            "\t".join(
                [
                    str(query_start),
                    str(query_end),
                    str(target_start),
                    str(target_end),
                    "R",
                    "chr22",
                    str(2000 + index * 100),
                    str(2059 + index * 100),
                    f"{2.0 + index / 10:.1f}",
                    "75.0",
                    "ParaPlus",
                    "1",
                    str(100 + index),
                    "60",
                    "0",
                    str(query_start + 29),
                    str(query_start + 29),
                    "A" * 60,
                    "G" * 60,
                ]
            )
        )
    return HEADER + "\n".join(rows) + "\n"


def config_payload(variant: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "commit": "a" * 40,
        "binary": "/tmp/fasim",
        "binary_sha256": "b" * 64,
        "query": "/tmp/query.fa",
        "query_sha256": "c" * 64,
        "target": "/tmp/target.fa",
        "target_sha256": "d" * 64,
        "rule": 0,
        "segment_len": 2048,
        "segment_overlap": 512,
        "grid_shifts": [0, 256],
        "grid_mode": "dual_grid",
        "max_segments": 4,
        "archive_first": True,
        "persistent_context": False,
        "segment_batch_size": 1,
        "device_memory_budget_bytes": 23622320128,
        "ownership_mode": "disabled",
        "exact_column_variant": variant,
        "exact_scoreinfo_gpu_max_per_task": 512,
        "traceback_certificate_mode": "disabled",
        "streams": 3,
        "gasal2_batch": 20000,
        "prune_max_per_task": 256,
        "gpu_ids": "0",
        "worker_count": 1,
        "merge_dedup_backend": "sqlite",
        "output_mode": "tfosorted",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["config_digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload


class IntegratedPairComparatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="fasim-phase7-pair-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_run(self, label: str, variant: str, wall: float) -> Path:
        root = self.root / label
        config = config_payload(variant)
        root.mkdir()
        (root / "run-config.json").write_text(
            json.dumps(config, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        enabled = 1 if variant == "gpu_pruned_scoreinfo_v1" else 0
        summary = {
            "config_digest_sha256": config["config_digest_sha256"],
            "pipeline_wall_seconds": f"{wall:.6f}",
            "segment_run_wall_seconds": f"{wall - 1:.6f}",
            "grid_shift_0_segment_count": "4",
            "grid_shift_256_segment_count": "4",
            "gasal2_requests": "1000",
            "gasal2_traceback_requests": "400",
            "exact_work_tasks": "200",
            "exact_work_cells": "1000000",
            "exact_stage_seconds": "20.000000" if not enabled else "10.000000",
            "traceback_host_observed_stage_seconds": "30.000000",
            "input_rows": "100",
            "output_rows": "80",
            "duplicate_rows": "20",
            "archive_input_bytes": "4096",
            "text_input_bytes": "0",
            "peak_rss_kb": "50000",
            "per_segment_full_text_emitted": "0",
            "bounded_memory_backend_active": "1",
            "exact_scoreinfo_gpu_pruned_output_enabled": str(enabled),
            "exact_scoreinfo_gpu_column_pruned_output_enabled": "0",
            "exact_scoreinfo_gpu_overflow_batches": "0",
            "exact_scoreinfo_gpu_fallback_batches": "0",
            "gasal2_fallbacks": "0",
            "length_guard_fallbacks": "0",
            "top5_offline_cluster_equal": "true",
            "top5_offline_cluster_overlap": "5",
            "decision": "segmented_query_kcnq1ot1_pilot_grid_stable",
        }
        (root / "summary.txt").write_text(
            "".join(f"{key}={value}\n" for key, value in summary.items()),
            encoding="utf-8",
        )
        for shift in (0, 256):
            grid = root / "grids" / f"shift_{shift}"
            grid.mkdir(parents=True)
            (grid / "merged-common-TFOsorted").write_text(output_text(), encoding="utf-8")
        return root

    def run_compare(
        self, baseline: Path, candidate: Path, allow_relocated_inputs: bool = False
    ) -> subprocess.CompletedProcess[str]:
        command = [
                "python3",
                str(COMPARE),
                "--workload",
                "fixture",
                "--repeat",
                "1",
                "--baseline-root",
                str(baseline),
                "--candidate-root",
                str(candidate),
                "--work-dir",
                str(self.root / "compare"),
                "--output",
                str(self.root / "pair.tsv"),
            ]
        if allow_relocated_inputs:
            command.append("--allow-relocated-input-paths")
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_validates_full_output_and_all_top5_contracts(self) -> None:
        baseline = self.make_run("baseline", "legacy_authority_scoreinfo", 100.0)
        candidate = self.make_run("candidate", "gpu_pruned_scoreinfo_v1", 80.0)

        result = self.run_compare(baseline, candidate)

        self.assertEqual(result.returncode, 0, result.stderr)
        with (self.root / "pair.tsv").open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(row["full_output_byte_equal"], "1")
        self.assertEqual(row["top5_score_equal"], "1")
        self.assertEqual(row["top5_stability_equal"], "1")
        self.assertEqual(row["top5_nt_score_equal"], "1")
        self.assertEqual(row["offline_clustered_top5_equal"], "1")
        self.assertEqual(row["exact_work_equal"], "1")
        self.assertEqual(row["speedup"], "1.250000")
        self.assertEqual(row["wall_reduction_percent"], "20.000000")
        self.assertEqual(row["fallbacks"], "0")

    def test_fails_closed_on_non_variant_config_drift(self) -> None:
        baseline = self.make_run("baseline", "legacy_authority_scoreinfo", 100.0)
        candidate = self.make_run("candidate", "gpu_pruned_scoreinfo_v1", 80.0)
        config_path = candidate / "run-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["gasal2_batch"] = 123
        canonical_payload = dict(config)
        canonical_payload.pop("config_digest_sha256")
        canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
        config["config_digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        config_path.write_text(json.dumps(config) + "\n", encoding="utf-8")

        result = self.run_compare(baseline, candidate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("config", result.stderr.lower())

    def test_fails_closed_on_full_output_drift(self) -> None:
        baseline = self.make_run("baseline", "legacy_authority_scoreinfo", 100.0)
        candidate = self.make_run("candidate", "gpu_pruned_scoreinfo_v1", 80.0)
        output = candidate / "grids" / "shift_0" / "merged-common-TFOsorted"
        output.write_text(output.read_text(encoding="utf-8") + output_text().splitlines()[1] + "\n")

        result = self.run_compare(baseline, candidate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("byte", result.stderr.lower())

    def test_allows_relocated_query_only_when_digest_is_equal(self) -> None:
        baseline = self.make_run("baseline", "legacy_authority_scoreinfo", 100.0)
        candidate = self.make_run("candidate", "gpu_pruned_scoreinfo_v1", 80.0)
        config_path = candidate / "run-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["query"] = "/different/materialized/path/query.fa"
        canonical_payload = dict(config)
        canonical_payload.pop("config_digest_sha256")
        canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
        config["config_digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        config_path.write_text(json.dumps(config) + "\n", encoding="utf-8")
        summary_path = candidate / "summary.txt"
        summary = summary_path.read_text(encoding="utf-8")
        summary = summary.replace(
            next(line for line in summary.splitlines() if line.startswith("config_digest_sha256=")),
            f"config_digest_sha256={config['config_digest_sha256']}",
        )
        summary_path.write_text(summary, encoding="utf-8")

        strict = self.run_compare(baseline, candidate)
        relocated = self.run_compare(baseline, candidate, allow_relocated_inputs=True)

        self.assertNotEqual(strict.returncode, 0)
        self.assertIn("query", strict.stderr)
        self.assertEqual(relocated.returncode, 0, relocated.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
