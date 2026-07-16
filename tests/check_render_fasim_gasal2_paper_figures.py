#!/usr/bin/env python3
"""Tests for frozen-source GASAL2 paper figure and table rendering."""

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "reproduce/render_figures.py"
SOURCE = ROOT / "paper/source_data"


def load_module():
    spec = importlib.util.spec_from_file_location("render_figures", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load render_figures module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PaperFigureRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.render = load_module()

    def test_figure1_layout_has_required_column_alignment(self) -> None:
        boxes = self.render.figure1_panel_boxes()
        self.assertEqual(boxes["B1"][:2], boxes["C"][:2])
        self.assertEqual(boxes["B2"][:2], boxes["D"][:2])
        self.assertEqual(boxes["B1"][3], boxes["B2"][3])
        self.assertEqual(boxes["C"][3], boxes["D"][3])

    def test_figure1_box_contract_is_converted_to_matplotlib_order(self) -> None:
        boxes = self.render.figure1_panel_boxes()
        self.assertEqual(
            self.render.matplotlib_panel_rectangle(boxes["B1"]),
            (0.06, 0.47, 0.42, 0.27),
        )
        self.assertEqual(
            self.render.matplotlib_panel_rectangle(boxes["D"]),
            (0.52, 0.08, 0.42, 0.27),
        )

    def test_primary_performance_filter_is_fast_topk_only(self) -> None:
        rows = self.render.read_tsv(SOURCE / "paired_speedup_summary.tsv")
        selected = self.render.primary_fast_topk_rows(rows)
        self.assertTrue(selected)
        self.assertTrue(
            all(row["output_contract"] == "fast_topk_score_stability_nt" for row in selected)
        )
        self.assertNotIn("c7_kcnq_max8_chr22", {row["workload_id"] for row in selected})

    def test_render_manifest_excludes_unrelated_paper_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "unrelated.md").write_text("not generated\n", encoding="utf-8")
            self.render.render_all(SOURCE, output)
            manifest = self.render.read_tsv(output / "figures/render_manifest.tsv")
            self.assertNotIn("unrelated.md", {row["path"] for row in manifest})

    def test_rendered_package_is_complete_600dpi_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first = Path(first_tmp)
            second = Path(second_tmp)
            self.render.render_all(SOURCE, first)
            self.render.render_all(SOURCE, second)

            relative_files = sorted(
                path.relative_to(first) for path in first.rglob("*") if path.is_file()
            )
            self.assertEqual(relative_files, sorted(
                path.relative_to(second) for path in second.rglob("*") if path.is_file()
            ))
            self.assertTrue(relative_files)
            for relative in relative_files:
                self.assertEqual(digest(first / relative), digest(second / relative), relative)

            for base in self.render.FIGURE_BASES:
                for suffix in (".svg", ".pdf", "_600dpi.png"):
                    self.assertTrue((first / "figures" / f"{base}{suffix}").is_file())
                svg_lines = (first / "figures" / f"{base}.svg").read_text(encoding="utf-8").splitlines()
                self.assertTrue(all(line == line.rstrip() for line in svg_lines))
                with Image.open(first / "figures" / f"{base}_600dpi.png") as image:
                    dpi = image.info.get("dpi")
                    self.assertIsNotNone(dpi)
                    self.assertAlmostEqual(dpi[0], 600, delta=1)
                    self.assertAlmostEqual(dpi[1], 600, delta=1)
                    self.assertGreaterEqual(image.width, 4000)

            for table in ("table1_workloads", "table2_performance", "table3_correctness", "table4_ablation_resources"):
                for suffix in (".tsv", ".md", ".tex"):
                    self.assertTrue((first / "tables" / f"{table}{suffix}").is_file())
            self.assertTrue((first / "supplementary/operating_envelope.tsv").is_file())
            self.assertTrue((first / "captions.md").is_file())
            self.assertTrue((first / "figures/source_mapping.tsv").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
