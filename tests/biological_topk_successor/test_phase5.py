from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
IMPLEMENTATION = ROOT / "reproduce/biological_topk_successor"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if str(IMPLEMENTATION) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATION))
freeze = load_module("freeze_phase5", IMPLEMENTATION / "freeze_phase5.py")
runner = load_module("biological_topk_phase6_runner_test", IMPLEMENTATION / "run_phase6.py")
analyzer = load_module("biological_topk_phase6_analyzer_test", IMPLEMENTATION / "analyze_phase6.py")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_single_fasta(path: Path) -> tuple[str, str]:
    headers: list[str] = []
    chunks: list[str] = []
    with path.open(encoding="ascii") as handle:
        for raw in handle:
            line = raw.rstrip("\r\n")
            if line.startswith(">"):
                headers.append(line[1:])
            elif line:
                chunks.append(line)
    if len(headers) != 1:
        raise AssertionError(f"expected one FASTA record in {path}")
    return headers[0], "".join(chunks)


def fasim_row(**updates: str) -> dict[str, str]:
    row = {
        "QueryStart": "1",
        "QueryEnd": "60",
        "StartInSeq": "1",
        "EndInSeq": "60",
        "Direction": "R",
        "Chr": "",
        "StartInGenome": "1",
        "EndInGenome": "60",
        "MeanStability": "2.5",
        "MeanIdentity(%)": "80",
        "Strand": "ParaPlus",
        "Rule": "1",
        "Score": "7",
        "Nt(bp)": "51",
        "Class": "0",
        "MidPoint": "30",
        "Center": "30",
        "TFO sequence": "A",
        "TTS sequence": "T",
    }
    row.update(updates)
    return row


class SuccessorPhase5Tests(unittest.TestCase):
    def test_fixed_bin_integration_includes_crossings_and_partial_final_bin(self) -> None:
        width = freeze.WINDOW_LENGTH
        values = freeze.integrated_fixed_bins(
            [(0, width + 3, 2.0), (width - 2, width + 2, 1.0)],
            width + 3,
        )
        np.testing.assert_allclose(
            values,
            np.array([2.0 + 2.0 / width, 8.0 / width]),
            rtol=0,
            atol=1e-15,
        )

    def test_signal_rule_reproduces_preregistered_feasibility_counts(self) -> None:
        receipt = json.loads((PAPER / "experimental_source_receipt.json").read_text(encoding="utf-8"))
        rule = receipt["source_counts"]["bte_linc01116_gse227804"]["signal_rule"]
        self.assertEqual(rule["threshold_candidate_counts"], {"4": 3324, "8": 830})
        self.assertEqual(rule["feasibility_chromosomes"], list(freeze.PRIMARY_CHROMOSOMES))
        self.assertEqual(rule["fixed_window_count_definition"], "ceil(primary_chromosome_length/4097)")
        self.assertEqual(rule["selection_strength"], "log1p(replicate)-log1p(control)")

    def test_manifest_and_single_record_targets_are_byte_bound(self) -> None:
        rows = read_tsv(PAPER / "experimental_benchmark_manifest.tsv")
        self.assertEqual(len(rows), 5000)
        self.assertEqual(len({row["region_id"] for row in rows}), 5000)
        self.assertTrue(all(re.fullmatch(r"bt5_[0-9a-f]{24}", row["region_id"]) for row in rows))
        by_dataset: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_dataset[row["dataset_id"]].append(row)
        self.assertEqual(len(by_dataset), 5)
        for dataset_id, dataset_rows in by_dataset.items():
            self.assertEqual(len(dataset_rows), 1000)
            self.assertEqual(sum(int(row["label"]) for row in dataset_rows), 100)
            ordered = sorted(dataset_rows, key=lambda row: int(row["fasta_order"]))
            self.assertEqual([row["region_id"] for row in ordered], sorted(row["region_id"] for row in ordered))
            target_path = ROOT / ordered[0]["target_fasta_path"]
            header, sequence = read_single_fasta(target_path)
            self.assertRegex(header, r"^t_[0-9a-f]{24}$")
            self.assertEqual(len(sequence), 1000 * 4097 + 999 * 4097)
            for index, row in enumerate(ordered):
                start = int(row["target_concat_start0"])
                end = int(row["target_concat_end0"])
                self.assertEqual((start, end), (index * 8194, index * 8194 + 4097))
                self.assertEqual(hashlib.sha256(sequence[start:end].encode("ascii")).hexdigest(), row["region_sequence_sha256"])
                if index < len(ordered) - 1:
                    self.assertEqual(sequence[end : end + 4097], "N" * 4097)
            query_header, query = read_single_fasta(ROOT / ordered[0]["query_fasta_path"])
            self.assertRegex(query_header, r"^q_[0-9a-f]{24}$")
            self.assertEqual(hashlib.sha256(query.encode("ascii")).hexdigest(), ordered[0]["query_sequence_sha256"])

    def test_negative_matching_and_selected_intervals_are_frozen(self) -> None:
        rows = read_tsv(PAPER / "experimental_benchmark_manifest.tsv")
        positives = {row["region_id"]: row for row in rows if row["label"] == "1"}
        intervals: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
        for row in rows:
            intervals[(row["dataset_id"], row["target_chromosome"])].append(
                (int(row["target_start0"]), int(row["target_end0"]))
            )
            if row["label"] == "0":
                matched = positives[row["matched_positive_region_id"]]
                self.assertEqual(row["dataset_id"], matched["dataset_id"])
                self.assertEqual(row["target_chromosome"], matched["target_chromosome"])
                self.assertLessEqual(float(row["gc_absolute_difference"]), 0.05)
                self.assertIn(int(row["negative_match_index"]), range(1, 10))
        for values in intervals.values():
            ordered = sorted(values)
            self.assertTrue(all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:])))

    def test_attempt_plan_is_label_blind_and_binds_all_three_arms(self) -> None:
        rows = read_tsv(PAPER / "experimental_attempt_plan.tsv")
        self.assertEqual(len(rows), 15)
        self.assertEqual({arm: sum(row["arm"] == arm for row in rows) for arm in ("A", "G", "X")}, {"A": 5, "G": 5, "X": 5})
        self.assertTrue(all(row["labels_visible_to_backend"] == "0" for row in rows))
        self.assertTrue(all(row["comparison_policy"] == "offline_after_all_15_attempts_terminal" for row in rows))
        self.assertEqual({row["runner_sha256"] for row in rows}, {runner.sha256_file(IMPLEMENTATION / "run_phase6.py")})
        self.assertEqual({row["analyzer_sha256"] for row in rows}, {analyzer.sha256_file(IMPLEMENTATION / "analyze_phase6.py")})

    def test_sandbox_mounts_only_the_attempt_work_directory(self) -> None:
        prefix = runner.bubblewrap_prefix(Path("/tmp/bt6-unit-work"))
        self.assertNotIn("/data", prefix)
        self.assertNotIn(str(ROOT), prefix)
        self.assertEqual(prefix[-5:], ["--bind", "/tmp/bt6-unit-work", "/work", "--chdir", "/work"])
        row = {
            "_partial_root": "/tmp/bt6-unit-work",
            "arm": "G",
            "cpu_affinity": "10-19",
            "gpu_physical_index": "0",
        }
        command, environment = runner.command_for(row)
        encoded = " ".join(command)
        self.assertNotIn("experimental_benchmark_manifest", encoded)
        self.assertNotIn(str(ROOT), encoded)
        self.assertIn("/work/inputs/query.fa", command)
        self.assertIn("/work/inputs/target.fa", command)
        self.assertEqual(environment["FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH"], "/work/telemetry.json")

    def test_target_mapping_uses_strand_specific_coordinate_contract(self) -> None:
        regions = [
            analyzer.Region("d", "l", "r1", 1, "chr1", 0, 100),
            analyzer.Region("d", "l", "r2", 0, "chr1", 200, 300),
            analyzer.Region("d", "l", "r3", 0, "chr1", 400, 500),
        ]
        self.assertEqual(analyzer.map_output_row(fasim_row(StartInSeq="201", EndInSeq="300"), regions), "r2")
        self.assertIsNone(analyzer.map_output_row(fasim_row(StartInSeq="200", EndInSeq="250"), regions))
        self.assertEqual(
            analyzer.map_output_row(
                fasim_row(Strand="ParaMinus", StartInSeq="200", EndInSeq="299"),
                regions,
            ),
            "r2",
        )
        self.assertIsNone(
            analyzer.map_output_row(
                fasim_row(Strand="ParaMinus", StartInSeq="200", EndInSeq="300"),
                regions,
            )
        )
        self.assertIsNone(analyzer.map_output_row(fasim_row(StartInSeq="101", EndInSeq="150"), regions))
        with self.assertRaises(analyzer.AnalysisError):
            analyzer.map_output_row(fasim_row(StartInSeq="0", EndInSeq="50"), regions)

    def test_streaming_region_score_uses_strict_nt_and_sentinel(self) -> None:
        regions = [
            analyzer.Region("d", "l", "r1", 1, "chr1", 0, 100),
            analyzer.Region("d", "l", "r2", 0, "chr1", 200, 300),
        ]
        rows = [
            fasim_row(Score="999", **{"Nt(bp)": "50"}),
            fasim_row(Score="7", **{"Nt(bp)": "51"}),
            fasim_row(Score="9", **{"Nt(bp)": "60"}),
            fasim_row(StartInSeq="101", EndInSeq="150", Score="100", **{"Nt(bp)": "60"}),
        ]
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "output.tsv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=analyzer.TFOSORTED_COLUMNS, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            scores, counts = analyzer.parse_fasim_scores(path, regions, query_length=100)
        self.assertEqual(scores, {"r1": 9, "r2": -1})
        self.assertEqual(counts, {"r1": 2, "r2": 0})

    def test_metrics_ties_and_zero_precision_are_deterministic(self) -> None:
        perfect_regions = [
            analyzer.Region("d", "l", "p1", 1, "chr1", 0, 1),
            analyzer.Region("d", "l", "p2", 1, "chr1", 1, 2),
            analyzer.Region("d", "l", "n1", 0, "chr1", 2, 3),
            analyzer.Region("d", "l", "n2", 0, "chr1", 3, 4),
        ]
        perfect = analyzer.dataset_metrics(perfect_regions, {"p1": 2, "p2": 2, "n1": 1, "n2": 1}, "G")
        self.assertEqual(perfect.aucpr, 1.0)
        self.assertEqual(perfect.precision_at_p, 1.0)
        zero_regions = [
            analyzer.Region("z", "l", "z1", 1, "chr1", 0, 1),
            analyzer.Region("z", "l", "z2", 1, "chr1", 1, 2),
            analyzer.Region("z", "l", "a1", 0, "chr1", 2, 3),
            analyzer.Region("z", "l", "a2", 0, "chr1", 3, 4),
        ]
        zero = analyzer.dataset_metrics(zero_regions, {region.region_id: -1 for region in zero_regions}, "G")
        self.assertTrue(zero.zero_precision)
        self.assertIsNone(zero.log_enrichment)
        self.assertTrue(math.isinf(analyzer.percentile_lcb([float("-inf")] + [1.0] * 19)))

    def test_bootstrap_is_paired_shared_and_seed_deterministic(self) -> None:
        regions: list[object] = []
        scores_a: dict[str, int] = {}
        scores_g: dict[str, int] = {}
        for outer in range(5):
            for index in range(10):
                region_id = f"r{outer}_{index}"
                label = int(index == 0)
                regions.append(analyzer.Region(f"d{outer}", f"l{outer}", region_id, label, "chr1", index, index + 1))
                scores_a[region_id] = 10 if label else 0
                scores_g[region_id] = 10 if label else 0
        first, first_meta = analyzer.paired_hierarchical_bootstrap(
            regions,
            {"A": scores_a, "G": scores_g},
            seed=17,
            replicates=20,
        )
        second, second_meta = analyzer.paired_hierarchical_bootstrap(
            regions,
            {"A": scores_a, "G": scores_g},
            seed=17,
            replicates=20,
        )
        self.assertEqual(first, second)
        self.assertEqual(first_meta, second_meta)
        self.assertTrue(first_meta["shared_resample_index_for_all_endpoints"])
        self.assertTrue(first_meta["paired_A_G_at_every_level"])
        self.assertTrue(all(values[0] == 0 and values[1] == 0 for values in first))


if __name__ == "__main__":
    unittest.main()
