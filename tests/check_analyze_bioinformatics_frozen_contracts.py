#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "reproduce" / "bioinformatics" / "analyze_frozen_contracts.py"
EXPECTED_WORKLOADS = {
    f"g{index:02d}_" for index in range(1, 14)
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class FrozenContractGeneratorPresenceTests(unittest.TestCase):
    def test_generator_exists(self) -> None:
        self.assertTrue(GENERATOR.is_file(), "frozen-contract generator is missing")


@unittest.skipUnless(GENERATOR.is_file(), "frozen-contract generator is missing")
class FrozenContractAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location(
            "analyze_frozen_contracts", GENERATOR
        )
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load frozen-contract generator")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.temp = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.temp.name) / "generated"
        artifact_rows = read_tsv(
            ROOT
            / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization/"
            "phase3-artifacts.tsv"
        )
        cls.expected_pair_outputs = {
            row["artifact_path"]
            for row in artifact_rows
            if row["artifact_path"].startswith("g")
            and "__pair" in row["artifact_path"]
            and "/output/" in row["artifact_path"]
            and row["artifact_path"].endswith("-TFOsorted")
        }
        cls.validated_pair_outputs: set[str] = set()
        cls.analyzed_pair_outputs: set[str] = set()
        original_validator = cls.module._validate_artifact
        original_loader = cls.module._load_comparator
        real_analyze = original_loader(ROOT)
        archive_root = (
            ROOT
            / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization"
        )

        def recording_validator(artifact_root, artifact_manifest, relative):
            path = original_validator(artifact_root, artifact_manifest, relative)
            if relative in cls.expected_pair_outputs:
                cls.validated_pair_outputs.add(relative)
            return path

        def recording_loader(repo_root):
            def recording_analyze(path, k, cluster_distance, cluster_length):
                cls.analyzed_pair_outputs.add(
                    path.relative_to(archive_root).as_posix()
                )
                return real_analyze(path, k, cluster_distance, cluster_length)

            return recording_analyze

        cls.module._validate_artifact = recording_validator
        cls.module._load_comparator = recording_loader
        try:
            cls.module.generate(ROOT, cls.output_dir)
        finally:
            cls.module._validate_artifact = original_validator
            cls.module._load_comparator = original_loader
        cls.contract_rows = read_tsv(cls.output_dir / "frozen_contract_matrix.tsv")
        cls.feature_rows = read_tsv(cls.output_dir / "mismatch_feature_matrix.tsv")

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "temp"):
            cls.temp.cleanup()

    def test_preserves_exact_supported_workloads_and_rank_rows(self) -> None:
        expected_ids = {
            row["workload_id"]
            for row in self.contract_rows
            if any(row["workload_id"].startswith(prefix) for prefix in EXPECTED_WORKLOADS)
        }
        self.assertEqual(len(self.contract_rows), 13)
        self.assertEqual(len(expected_ids), 13)
        self.assertEqual(len(self.feature_rows), 39)
        self.assertEqual(
            {(row["workload_id"], row["rank"]) for row in self.feature_rows},
            {(workload, rank) for workload in expected_ids for rank in ("score", "stability", "nt")},
        )

    def test_frozen_gate_counts_and_full_row_diagnostics_are_exact(self) -> None:
        self.assertTrue(
            {"score_mismatch", "stability_mismatch", "nt_mismatch"}.issubset(
                self.contract_rows[0]
            )
        )
        self.assertEqual(sum(int(row["score_clean"]) for row in self.contract_rows), 13)
        self.assertEqual(sum(int(row["stability_clean"]) for row in self.contract_rows), 11)
        self.assertEqual(sum(int(row["nt_clean"]) for row in self.contract_rows), 12)
        self.assertEqual(sum(int(row["all_ranked_clean"]) for row in self.contract_rows), 10)
        self.assertEqual(sum(int(row["full_row_equal"]) for row in self.contract_rows), 0)
        for row in self.contract_rows:
            for rank in ("score", "stability", "nt"):
                self.assertEqual(
                    int(row[f"{rank}_clean"]) + int(row[f"{rank}_mismatch"]), 1
                )
        self.assertTrue(
            all(
                int(row["full_missing_rows_total"]) > 0
                or int(row["full_extra_rows_total"]) > 0
                for row in self.contract_rows
            )
        )
        by_workload = {row["workload_id"]: row for row in self.contract_rows}
        g05 = by_workload["g05_neat1_mid_2812_chr11"]
        self.assertEqual(g05["repeat_contract_status_consistent"], "1")
        self.assertEqual(g05["output_digest_repeat_consistent"], "0")

    def test_g05_repeat_basis_does_not_claim_identical_output_digests(self) -> None:
        expected = (
            "three_frozen_pairs_with_identical_contract_flags_but_varying_"
            "full_output_digests"
        )
        contract_by_workload = {
            row["workload_id"]: row for row in self.contract_rows
        }
        g05_contract = contract_by_workload["g05_neat1_mid_2812_chr11"]
        self.assertEqual(
            g05_contract["baseline_output_digest_repeat_consistent"], "1"
        )
        self.assertEqual(
            g05_contract["candidate_output_digest_repeat_consistent"], "0"
        )
        self.assertEqual(g05_contract["repeat_consistency_basis"], expected)
        g05_features = [
            row
            for row in self.feature_rows
            if row["workload_id"] == "g05_neat1_mid_2812_chr11"
        ]
        self.assertEqual(len(g05_features), 3)
        self.assertEqual(
            {row["repeat_consistency_basis"] for row in g05_features}, {expected}
        )
        report = (self.output_dir / "mismatch_analysis.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "g05 candidate full-output digests vary across its three frozen pairs",
            report,
        )

    def test_repeat_status_and_top5_signatures_are_distinct_evidence(self) -> None:
        by_workload = {row["workload_id"]: row for row in self.contract_rows}
        g05 = by_workload["g05_neat1_mid_2812_chr11"]
        self.assertTrue(
            {
                "repeat_contract_status_consistent",
                "baseline_repeat_top5_signature_consistent",
                "candidate_repeat_top5_signature_consistent",
                "repeat_top5_signature_consistent",
                "repeat_top5_signature_availability_reason",
            }.issubset(g05),
            "repeat status/signature fields are missing",
        )
        self.assertEqual(g05["repeat_contract_status_consistent"], "1")
        self.assertEqual(g05["baseline_repeat_top5_signature_consistent"], "1")
        self.assertEqual(g05["candidate_repeat_top5_signature_consistent"], "1")
        self.assertEqual(g05["repeat_top5_signature_consistent"], "1")
        self.assertEqual(g05["candidate_output_digest_repeat_consistent"], "0")

        g12 = by_workload["g12_h19_full_chr22"]
        self.assertEqual(g12["repeat_contract_status_consistent"], "1")
        self.assertEqual(g12["baseline_repeat_top5_signature_consistent"], "NA")
        self.assertEqual(g12["candidate_repeat_top5_signature_consistent"], "NA")
        self.assertEqual(g12["repeat_top5_signature_consistent"], "NA")
        self.assertEqual(
            g12["repeat_top5_signature_availability_reason"],
            "single_frozen_pair_no_multi_repeat_test",
        )
        self.assertNotIn("repeat_consistent", g12)

        g05_features = [
            row
            for row in self.feature_rows
            if row["workload_id"] == "g05_neat1_mid_2812_chr11"
        ]
        self.assertEqual(
            {row["repeat_top5_signature_consistent"] for row in g05_features},
            {"1"},
        )
        g12_features = [
            row
            for row in self.feature_rows
            if row["workload_id"] == "g12_h19_full_chr22"
        ]
        self.assertEqual(
            {row["repeat_top5_signature_consistent"] for row in g12_features},
            {"NA"},
        )
        self.assertTrue(
            all("repeat_signature_consistent" not in row for row in self.feature_rows)
        )
        report = (self.output_dir / "mismatch_analysis.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "g05 has stable baseline and candidate clustered top-five signatures "
            "across three pairs despite varying candidate full-output digests.",
            report,
        )
        self.assertIn(
            "g12 has one frozen pair, so multi-repeat top-five signature "
            "consistency is `NA`.",
            report,
        )

    def test_mismatch_positions_and_repeat_signatures_are_preserved(self) -> None:
        by_key = {
            (row["workload_id"], row["rank"]): row for row in self.feature_rows
        }
        expected = {
            ("g02_malat1_mid_2048_chr21", "stability"): "2,3,4,5",
            ("g09_kcnq1ot1_3p_2048_chr11", "nt"): "5",
            ("g12_h19_full_chr22", "stability"): "2",
        }
        observed = {
            key: row["differing_positions"]
            for key, row in by_key.items()
            if row["rank_equal"] == "0"
        }
        self.assertEqual(observed, expected)
        self.assertEqual(by_key[("g02_malat1_mid_2048_chr21", "stability")]["repeat_count"], "3")
        self.assertEqual(by_key[("g02_malat1_mid_2048_chr21", "stability")]["repeat_top5_signature_consistent"], "1")
        self.assertEqual(by_key[("g09_kcnq1ot1_3p_2048_chr11", "nt")]["repeat_count"], "3")
        self.assertEqual(by_key[("g09_kcnq1ot1_3p_2048_chr11", "nt")]["repeat_top5_signature_consistent"], "1")
        self.assertEqual(by_key[("g12_h19_full_chr22", "stability")]["repeat_count"], "1")
        self.assertEqual(
            by_key[("g12_h19_full_chr22", "stability")]["repeat_consistency_basis"],
            "single_frozen_pair_no_multi_repeat_test",
        )
        self.assertTrue(
            all(
                row["differing_positions"] == "none"
                for row in self.feature_rows
                if row["rank_equal"] == "1"
            )
        )

    def test_feature_rows_have_composition_boundaries_and_explicit_availability(self) -> None:
        required = {
            "query_a_count",
            "query_c_count",
            "query_g_count",
            "query_t_count",
            "query_normalized_sha256",
            "baseline_top5_identities",
            "candidate_top5_identities",
            "baseline_primary_values",
            "candidate_primary_values",
            "baseline_rank5_rank6_primary_margin",
            "candidate_rank5_rank6_primary_margin",
            "baseline_rank5_rank6_primary_equal",
            "candidate_rank5_rank6_primary_equal",
            "comparator_boundary_ties_equal",
            "baseline_comparator_tie_groups_all_ranks",
            "candidate_comparator_tie_groups_all_ranks",
            "baseline_output_rows",
            "candidate_output_rows",
            "allocation_state",
            "allocation_state_availability_reason",
            "runtime_telemetry_available",
        }
        self.assertTrue(required.issubset(self.feature_rows[0]))
        for row in self.feature_rows:
            composition = sum(int(row[f"query_{base}_count"]) for base in "acgt")
            self.assertEqual(composition, int(row["query_length_nt"]))
            self.assertEqual(len(row["query_normalized_sha256"]), 64)
            self.assertNotEqual(row["baseline_rank5_rank6_primary_margin"], "NA")
            self.assertNotEqual(row["candidate_rank5_rank6_primary_margin"], "NA")
            self.assertEqual(row["allocation_state"], "NA")
            self.assertEqual(
                row["allocation_state_availability_reason"],
                "not_recorded_in_frozen_development_evidence",
            )
            self.assertEqual(row["runtime_telemetry_available"], "1")

    def test_primary_equality_is_not_a_comparator_rank_tuple_tie(self) -> None:
        self.assertTrue(
            hasattr(self.module, "comparator_rank_values"),
            "comparator rank-tuple helper is missing",
        )
        rank5 = {"Score": "100", "Nt(bp)": "80", "MeanStability": "2.5"}
        rank6 = {"Score": "100", "Nt(bp)": "79", "MeanStability": "2.5"}
        self.assertEqual(
            self.module.primary_value(rank5, "score"),
            self.module.primary_value(rank6, "score"),
        )
        self.assertNotEqual(
            self.module.comparator_rank_values(rank5, "score"),
            self.module.comparator_rank_values(rank6, "score"),
        )
        self.assertIn("comparator_boundary_ties_all_equal", self.contract_rows[0])
        self.assertIn("baseline_comparator_tie_groups_total", self.contract_rows[0])
        self.assertIn("candidate_comparator_tie_groups_total", self.contract_rows[0])
        self.assertNotIn("boundary_ties_all_equal", self.contract_rows[0])
        report = (self.output_dir / "mismatch_analysis.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "A zero primary margin means only that rank 5 and rank 6 have equal "
            "primary values.",
            report,
        )
        self.assertIn(
            "Comparator ties require equality of the complete score/stability/Nt "
            "ranking tuple.",
            report,
        )
        self.assertNotIn("A zero margin marks a tied top-K boundary", report)

    def test_repeat_signature_equality_uses_full_rows_not_compact_hashes(self) -> None:
        self.assertTrue(
            hasattr(self.module, "repeat_top5_signature_consistent"),
            "full-row repeat signature helper is missing",
        )
        first = {column: f"first-{column}" for column in self.module.TFOSORTED_COLUMNS}
        second = dict(first)
        second["Score"] = "different-score"
        self.assertEqual(
            self.module.repeat_top5_signature_consistent([[first], [dict(first)]]),
            1,
        )
        self.assertEqual(
            self.module.repeat_top5_signature_consistent([[first], [second]]),
            0,
        )
        self.assertIsNone(self.module.repeat_top5_signature_consistent([[first]]))

    def test_generation_is_byte_stable_and_matches_checked_in_outputs(self) -> None:
        first = {
            name: (self.output_dir / name).read_bytes()
            for name in (
                "frozen_contract_matrix.tsv",
                "mismatch_feature_matrix.tsv",
                "mismatch_analysis.md",
            )
        }
        self.module.generate(ROOT, self.output_dir)
        second = {name: (self.output_dir / name).read_bytes() for name in first}
        self.assertEqual(first, second)
        for name, payload in first.items():
            self.assertEqual(payload, (ROOT / "paper" / "bioinformatics" / name).read_bytes())

    def test_publication_rolls_back_after_each_atomic_replace(self) -> None:
        self.assertTrue(
            hasattr(self.module, "publish_outputs_transactionally"),
            "transactional publisher is missing",
        )
        names = (
            "frozen_contract_matrix.tsv",
            "mismatch_feature_matrix.tsv",
            "mismatch_analysis.md",
        )
        old = {name: f"old:{name}\n".encode("ascii") for name in names}
        new = {name: f"new:{name}\n" for name in names}

        class InjectedPublishFailure(BaseException):
            pass

        for fail_after in (1, 2, 3):
            with self.subTest(fail_after=fail_after), tempfile.TemporaryDirectory() as temp_dir:
                parent = Path(temp_dir)
                output_dir = parent / "bioinformatics"
                output_dir.mkdir()
                for name, payload in old.items():
                    (output_dir / name).write_bytes(payload)

                def fail(step: int, name: str) -> None:
                    if step == fail_after:
                        raise InjectedPublishFailure(name)

                with self.assertRaises(InjectedPublishFailure):
                    self.module.publish_outputs_transactionally(
                        output_dir, new, after_replace=fail
                    )

                self.assertEqual(
                    {name: (output_dir / name).read_bytes() for name in names}, old
                )
                self.assertEqual({path.name for path in output_dir.iterdir()}, set(names))
                self.assertEqual(list(parent.iterdir()), [output_dir])

    def test_validates_every_paired_output_before_digest_consistency_claims(self) -> None:
        self.assertEqual(len(self.expected_pair_outputs), 62)
        self.assertEqual(self.validated_pair_outputs, self.expected_pair_outputs)

    def test_analyzes_every_paired_output_for_repeat_top5_signatures(self) -> None:
        self.assertEqual(len(self.expected_pair_outputs), 62)
        self.assertEqual(self.analyzed_pair_outputs, self.expected_pair_outputs)

    def test_report_states_scope_without_proposing_an_allowlist_or_guard(self) -> None:
        report = (self.output_dir / "mismatch_analysis.md").read_text(encoding="utf-8")
        for statement in (
            "13/13 score-ranked workloads are clean",
            "10/13 workloads are clean across all three ranked contracts",
            "0/13 workloads have full-row equality",
            "No deterministic, query-independent pre-run or runtime mechanism certificate",
            "No query-name, gene-ID, or sequence-digest allowlist is proposed",
            "paper-data-v1-dccfd49-20260716",
            "generalization_mismatch_top5_pre_freeze.tsv",
            "paper/source_data/generalization_pairs_pre_freeze.tsv",
            "paper/source_data/generalization_runs_pre_freeze.tsv",
            "paper/workload_manifest.tsv",
            "first 16 hexadecimal characters of SHA-256",
        ):
            self.assertIn(statement, report)

    def test_checksum_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source.tsv"
            path.write_text("a\tb\n1\t2\n", encoding="utf-8")
            expected = self.module.sha256_file(path)
            path.write_text("a\tb\n1\t3\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum drift"):
                self.module.validate_sha256(path, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
