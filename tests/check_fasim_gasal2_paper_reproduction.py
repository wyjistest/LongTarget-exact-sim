#!/usr/bin/env python3
"""Contract checks for the GASAL2 paper reproduction package."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise AssertionError(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


class PaperReproductionPackageTests(unittest.TestCase):
    def test_input_manifest_has_unique_digest_aware_reconstruction(self) -> None:
        path = ROOT / "reproduce/input_manifest.tsv"
        fields, rows = read_tsv(path)
        self.assertEqual(
            fields,
            [
                "input_id", "kind", "source", "license", "path_convention",
                "size_bytes", "sha256", "required_for", "tracked_or_external",
                "reconstruction_command",
            ],
        )
        self.assertEqual(len(rows), 13)
        self.assertEqual(len({row["input_id"] for row in rows}), 13)
        self.assertEqual(len({row["sha256"] for row in rows}), 13)
        for row in rows:
            self.assertFalse(Path(row["path_convention"]).is_absolute())
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn(row["tracked_or_external"], {"tracked", "external"})
            self.assertNotIn("/data/", row["reconstruction_command"])
            self.assertTrue(row["source"] and row["license"] and row["reconstruction_command"])
        sources = "\n".join(row["source"] for row in rows)
        self.assertIn("https://github.com/LongTarget/Fasim-LongTarget", sources)
        self.assertIn("https://rest.ensembl.org/sequence/id/ENST00000597346", sources)
        self.assertIn("https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips", sources)

    def test_environment_manifest_and_notes_separate_observation_from_guidance(self) -> None:
        payload = json.loads((ROOT / "reproduce/environment_manifest.json").read_text(encoding="utf-8"))
        for key in (
            "schema_version", "os", "kernel", "cpu_model", "logical_cpus",
            "ram_bytes", "gpus", "nvidia_driver", "cuda_toolkit", "cxx",
            "python", "gasal2_commit", "gasal2_gpu_sm_arch", "gasal2_max_query_len",
        ):
            self.assertIn(key, payload)
        self.assertEqual(payload["gasal2_max_query_len"], 2812)
        self.assertEqual(len(payload["gpus"]), 2)
        notes = (ROOT / "reproduce/environment.md").read_text(encoding="utf-8")
        for phrase in (
            "Automatically Captured Facts",
            "Manual Protocol Notes",
            "Host NVIDIA driver is not supplied by the container",
            "one worker per GPU",
            "not controlled",
        ):
            self.assertIn(phrase, notes)

    def test_reproduction_commands_are_tiered_and_bounded(self) -> None:
        commands = (ROOT / "reproduce/benchmark_commands.sh").read_text(encoding="utf-8")
        for tier in ("quick", "source-data", "figures", "core-gpu", "max8"):
            self.assertIn(f'case "$TIER" in', commands) if tier == "quick" else None
            self.assertRegex(commands, rf"(?m)^{re.escape(tier)}\)$", tier)
        self.assertIn("check-fasim-gasal2-paper-reproduction", commands)
        self.assertIn("run_fasim_gasal2_paper_phase2.py", commands)
        self.assertIn("c7_kcnq_max8_chr22", commands)
        self.assertNotIn("full 121", commands.lower())
        self.assertNotIn("full hg38", commands.lower())

    def test_container_release_and_quick_checker_boundaries(self) -> None:
        dockerfile = (ROOT / "reproduce/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("nvidia/cuda:12.5", dockerfile)
        self.assertIn("matplotlib==3.9.1", dockerfile)
        checker = (ROOT / "reproduce/check_reproduction.sh").read_text(encoding="utf-8")
        self.assertIn("source_data_manifest.tsv", checker)
        self.assertIn("render_figures.py", checker)
        self.assertNotIn(".paper-artifacts", checker)
        release = (ROOT / "paper/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
        self.assertIn("gasal2-longtarget-paper-v0.1", release)
        self.assertIn("Do not create or push the tag as part of paper preparation", release)

    @unittest.skipUnless(
        (ROOT / ".tmp/gasal2_hg38_archive_first_run/shards/chr22.fa").is_file(),
        "external hg38 shard is not available",
    )
    def test_input_helper_reconstructs_frozen_combined_and_slice_digests(self) -> None:
        helper = ROOT / "reproduce/prepare_inputs.py"
        shards = ROOT / ".tmp/gasal2_hg38_archive_first_run/shards"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            subprocess.run(
                [
                    "python3", str(helper), "combine", "--output", str(output / "combined.fa"),
                    str(shards / "chr21.fa"), str(shards / "chr22.fa"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "python3", str(helper), "slice", "--input", str(shards / "chr22.fa"),
                    "--output", str(output / "slice.fa"), "--start", "10000000",
                    "--end", "12000000", "--header", "chr22_slice_10m_12m", "--width", "80",
                ],
                check=True,
            )
            self.assertEqual(
                hashlib.sha256((output / "combined.fa").read_bytes()).hexdigest(),
                "101496c0ff86af1227b8923b5c7af6be2c0e0edabee86b260cd1a539f93359d6",
            )
            self.assertEqual(
                hashlib.sha256((output / "slice.fa").read_bytes()).hexdigest(),
                "e36fd5e349179420d36f7a2cca4503dbe1e82ad4d7eecb88afd421f0f23099ea",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
