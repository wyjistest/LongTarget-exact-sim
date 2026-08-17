from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from reproduce.biological_topk import (
    build_phase2_regression as builder,
    canonicalize_rows,
    compare_candidate_topk,
    contract,
    exact_binomial_bounds,
    match_candidate_sites,
    rank_diagnostics,
    recluster_candidate_sites,
)


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
SPEC = compare_candidate_topk.load_contract_spec(PAPER / "contract_spec.json")


def load_fixture(workload_id: str):
    fixture = next(
        fixture
        for fixture in builder.holdout_fixtures()
        if fixture.workload_id == workload_id and fixture.repeat_id == "0"
    )
    identity = builder._identity(fixture, SPEC["parameter_bundle_sha256"])
    authority_mapping = builder._receipt_mapping(fixture, arm="A", identity=identity)
    candidate_mapping = builder._receipt_mapping(fixture, arm="G", identity=identity)
    authority = canonicalize_rows.receipt_from_mapping(
        authority_mapping,
        base_directory=ROOT,
    )
    candidate = canonicalize_rows.receipt_from_mapping(
        candidate_mapping,
        base_directory=ROOT,
    )
    return fixture, authority_mapping, candidate_mapping, authority, candidate


def rankings(path: Path, receipt: canonicalize_rows.InputReceipt):
    validated = canonicalize_rows.validate_receipt_files(receipt, path)
    rows = canonicalize_rows.canonicalize_output(path, validated)
    return recluster_candidate_sites.all_rankings(rows, receipt)


class Phase2ComparatorTests(unittest.TestCase):
    def test_frozen_tfosorted_columns_match_archive_authority(self) -> None:
        from scripts.fasim_tfo_archive import TFOSORTED_COLUMNS

        self.assertEqual(canonicalize_rows.TFOSORTED_COLUMNS, TFOSORTED_COLUMNS)

    def test_optimized_legacy_assignments_match_every_golden_fixture(self) -> None:
        with (PAPER / "legacy_clustering_fixtures.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        by_fixture: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            by_fixture.setdefault(row["fixture_id"], []).append(row)
        for fixture_id, fixture_rows in by_fixture.items():
            legacy = [
                contract.LegacyRow(
                    int(row["raw_QueryStart"]),
                    int(row["raw_QueryEnd"]),
                    int(row["raw_Nt_bp"]),
                    index,
                )
                for index, row in enumerate(fixture_rows)
            ]
            expected = contract.cluster_legacy(legacy)
            observed = recluster_candidate_sites.legacy_midpoint_assignments(
                [
                    (
                        contract.legacy_query_midpoint(row.raw_query_start, row.raw_query_end),
                        row.nt,
                    )
                    for row in legacy
                ]
            )
            actual_rows = [
                observed.get(row.middle) if row.motif else None
                for row in expected
            ]
            expected_rows = [
                (row.motif, row.center) if row.motif else None
                for row in expected
            ]
            self.assertEqual(actual_rows, expected_rows, fixture_id)

    def test_optimized_legacy_assignments_match_deterministic_fuzz(self) -> None:
        generator = random.Random(20260730)
        for case in range(50):
            legacy = []
            for index in range(generator.randint(1, 16)):
                start = generator.randint(40, 180)
                end = start + generator.randint(40, 80)
                legacy.append(
                    contract.LegacyRow(start, end, generator.randint(49, 70), index)
                )
            expected = contract.cluster_legacy(legacy)
            observed = recluster_candidate_sites.legacy_midpoint_assignments(
                [
                    (
                        contract.legacy_query_midpoint(row.raw_query_start, row.raw_query_end),
                        row.nt,
                    )
                    for row in legacy
                ]
            )
            self.assertEqual(
                [observed.get(row.middle) if row.motif else None for row in expected],
                [(row.motif, row.center) if row.motif else None for row in expected],
                case,
            )

    def test_known_hq10_and_hq11_mismatches_are_site_preserving(self) -> None:
        expected = {
            "hq10_ht02": ("stability", "representation-only difference", "1"),
            "hq11_ht02": ("score", "same candidate site endpoint shift", "62/65"),
        }
        for workload, (mode, classification, minimum_overlap) in expected.items():
            fixture, _, _, authority, candidate = load_fixture(workload)
            result, details = compare_candidate_topk.compare(
                authority_path=fixture.authority_output,
                candidate_path=fixture.candidate_output,
                authority_receipt=authority,
                candidate_receipt=candidate,
                contract_spec=SPEC,
            )
            self.assertEqual(result["comparison_status"], "pass")
            self.assertEqual(result["strict_row_diagnostic"], "mismatch")
            self.assertTrue(all(row["set_membership"] == "preserved" for row in result["modes"].values()))
            self.assertIn(classification, result["modes"][mode]["classifications"])
            overlaps = [
                row["target_overlap"]
                for row in details
                if row["ranking_mode"] == mode and row["detail_kind"] == "matched"
            ]
            self.assertEqual(min(overlaps, key=builder._fraction_value), minimum_overlap)

    def test_comparator_modules_contain_no_known_workload_special_case(self) -> None:
        for relative in (
            "reproduce/biological_topk/canonicalize_rows.py",
            "reproduce/biological_topk/recluster_candidate_sites.py",
            "reproduce/biological_topk/match_candidate_sites.py",
            "reproduce/biological_topk/compare_candidate_topk.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("hq10", text.lower(), relative)
            self.assertNotIn("hq11", text.lower(), relative)

    def test_input_identity_mismatch_stops_before_missing_outputs_are_read(self) -> None:
        fixture, authority_mapping, candidate_mapping, _, _ = load_fixture("hq10_ht02")
        changed = dict(candidate_mapping["input_identity"])
        changed["query_ordinal_namespace"] = "different_namespace"
        changed["input_pair_digest"] = contract.input_pair_digest(changed)
        candidate_mapping = dict(candidate_mapping)
        candidate_mapping["input_identity"] = changed
        authority_mapping = dict(authority_mapping)
        authority_mapping["output_sha256"] = "0" * 64
        authority_mapping["query_fasta"] = "/missing/query.fa"
        candidate_mapping["output_sha256"] = "0" * 64
        candidate_mapping["target_fasta"] = "/missing/target.fa"
        authority = canonicalize_rows.receipt_from_mapping(authority_mapping, base_directory=ROOT)
        candidate = canonicalize_rows.receipt_from_mapping(candidate_mapping, base_directory=ROOT)
        result, _ = compare_candidate_topk.compare(
            authority_path=Path("/missing/authority"),
            candidate_path=Path("/missing/candidate"),
            authority_receipt=authority,
            candidate_receipt=candidate,
            contract_spec=SPEC,
        )
        self.assertFalse(result["matching_started"])
        self.assertTrue(result["technical_failure"])
        self.assertIn("query_ordinal_namespace", result["input_identity_mismatches"])
        self.assertEqual(result["technical_failure_reason"], "input_identity_mismatch")

    def test_all_required_scientific_classifications_are_reachable(self) -> None:
        fixture, _, _, authority_receipt, _ = load_fixture("hq11_ht02")
        authority_rankings = rankings(fixture.authority_output, authority_receipt)
        first, second = authority_rankings["score"][:2]

        swapped = (
            dataclasses.replace(second, arm="G", rank=1),
            dataclasses.replace(first, arm="G", rank=2),
        )
        displaced, _ = match_candidate_sites.compare_ranked_sites((first, second), swapped)
        self.assertIn("set-preserving rank displacement", displaced["classifications"])

        far = dataclasses.replace(
            first,
            arm="G",
            rank=2,
            representative_target_start0=first.representative_target_start0 + 10000,
            representative_target_end0=first.representative_target_end0 + 10000,
        )
        extra, _ = match_candidate_sites.compare_ranked_sites(
            (first,),
            (dataclasses.replace(first, arm="G"), far),
        )
        self.assertIn("extra candidate site", extra["classifications"])
        missing, _ = match_candidate_sites.compare_ranked_sites(
            (first, second),
            (dataclasses.replace(first, arm="G"),),
        )
        self.assertIn("missing candidate site", missing["classifications"])
        substitution, _ = match_candidate_sites.compare_ranked_sites((first,), (far,))
        self.assertIn("true candidate-site substitution", substitution["classifications"])

        duplicate_authority = (first, dataclasses.replace(first, rank=2))
        duplicate_candidate = (
            dataclasses.replace(first, arm="G"),
            dataclasses.replace(first, arm="G", rank=2),
        )
        ambiguous, _ = match_candidate_sites.compare_ranked_sites(
            duplicate_authority,
            duplicate_candidate,
        )
        self.assertTrue(ambiguous["ambiguous_matching"])
        self.assertIn("ambiguous matching", ambiguous["classifications"])

    def test_default_cli_is_fail_closed_for_scientific_mismatch(self) -> None:
        fixture, authority_mapping, candidate_mapping, _, _ = load_fixture("hq10_ht02")
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            empty_output = directory / "empty-TFOsorted"
            empty_output.write_text(
                "\t".join(canonicalize_rows.TFOSORTED_COLUMNS) + "\n",
                encoding="utf-8",
            )
            for mapping in (authority_mapping, candidate_mapping):
                mapping["query_fasta"] = str(ROOT / mapping["query_fasta"])
                mapping["target_fasta"] = str(ROOT / mapping["target_fasta"])
            candidate_mapping["output_sha256"] = hashlib.sha256(empty_output.read_bytes()).hexdigest()
            authority_receipt = directory / "authority.json"
            candidate_receipt = directory / "candidate.json"
            authority_receipt.write_text(json.dumps(authority_mapping), encoding="utf-8")
            candidate_receipt.write_text(json.dumps(candidate_mapping), encoding="utf-8")
            output_json = directory / "result.json"
            details = directory / "details.tsv"
            command = (
                sys.executable,
                str(ROOT / "reproduce/biological_topk/compare_candidate_topk.py"),
                "--authority",
                str(fixture.authority_output),
                "--candidate",
                str(empty_output),
                "--authority-receipt",
                str(authority_receipt),
                "--candidate-receipt",
                str(candidate_receipt),
                "--contract-spec",
                str(PAPER / "contract_spec.json"),
                "--output-json",
                str(output_json),
                "--details-tsv",
                str(details),
            )
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr.decode())
            self.assertEqual(
                json.loads(output_json.read_text(encoding="utf-8"))["comparison_status"],
                "scientific_mismatch",
            )
            permissive = subprocess.run(
                (*command, "--no-fail-closed"),
                cwd=ROOT,
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(permissive.returncode, 0, permissive.stderr.decode())

    def test_exact_statistics_and_rank_diagnostics_are_not_binary_float(self) -> None:
        bound = exact_binomial_bounds.exact_binomial_bound(60, 60)
        self.assertTrue(bound["lower_confidence_bound"].startswith("0.95129708668990249"))
        diagnostic = rank_diagnostics.rank_diagnostics(
            3,
            3,
            ((0, 1), (1, 0), (2, 2)),
        )
        self.assertEqual(diagnostic["finite_rbo_fraction"], "123867/200000")
        self.assertEqual(
            [row["candidate_minus_authority"] for row in diagnostic["rank_displacements"]],
            [1, -1, 0],
        )

    def test_frozen_regression_receipt_has_zero_technical_failures(self) -> None:
        receipt = json.loads((PAPER / "phase2_regression_receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["comparison_count"], 184)
        self.assertEqual(receipt["ranking_result_count"], 552)
        self.assertEqual(receipt["technical_failure_count"], 0)
        self.assertEqual(receipt["input_identity_mismatch_count"], 0)
        self.assertEqual(receipt["ambiguous_matching_result_count"], 0)
        self.assertFalse(receipt["fresh_pair_selected"])
        self.assertFalse(receipt["new_prediction_run"])
        self.assertFalse(receipt["independent_validation_claim"])


if __name__ == "__main__":
    unittest.main()
