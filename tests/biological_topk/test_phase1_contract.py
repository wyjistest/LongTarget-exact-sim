from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import importlib.util
import json
import sys
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONTRACT = load_module(
    "biological_topk_contract",
    ROOT / "reproduce/biological_topk/contract.py",
)
CHECKER = load_module(
    "biological_topk_phase1_checker",
    ROOT / "scripts/check_biological_topk_phase.py",
)
PAPER = ROOT / "paper/biological_topk"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class Phase1ContractTests(unittest.TestCase):
    def test_legacy_golden_fixture_replays_byte_level_expectations(self) -> None:
        rows = read_tsv(PAPER / "legacy_clustering_fixtures.tsv")
        by_fixture: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            by_fixture.setdefault(row["fixture_id"], []).append(row)
        self.assertEqual(
            set(by_fixture),
            {"nt_boundary", "midpoint_parity", "dynamic_map_strict_ties", "motif_assignment_order"},
        )
        for fixture_rows in by_fixture.values():
            clustered = CONTRACT.cluster_legacy(
                [
                    CONTRACT.LegacyRow(
                        int(row["raw_QueryStart"]),
                        int(row["raw_QueryEnd"]),
                        int(row["raw_Nt_bp"]),
                        index,
                    )
                    for index, row in enumerate(fixture_rows)
                ]
            )
            observed = [
                (row.middle, row.motif, row.center, row.neartriplex)
                for row in clustered
            ]
            expected = [
                (
                    int(row["expected_legacy_midpoint"]),
                    int(row["expected_motif"]),
                    int(row["expected_center"]),
                    int(row["expected_neartriplex"]),
                )
                for row in fixture_rows
            ]
            self.assertEqual(observed, expected)

    def test_nt_boundary_and_midpoint_parity(self) -> None:
        rows = [
            CONTRACT.LegacyRow(101, 149, 49, 0),
            CONTRACT.LegacyRow(101, 150, 50, 1),
            CONTRACT.LegacyRow(101, 151, 51, 2),
            CONTRACT.LegacyRow(102, 151, 51, 3),
        ]
        result = CONTRACT.cluster_legacy(rows)
        self.assertEqual([row.motif for row in result[:2]], [0, 0])
        self.assertEqual(result[2].middle, 126)
        self.assertEqual(result[3].middle, 126)
        self.assertGreater(result[2].motif, 0)

    def test_legacy_tie_is_strict_and_first_position_wins(self) -> None:
        result = CONTRACT.cluster_legacy([CONTRACT.LegacyRow(101, 151, 51, 0)])
        self.assertEqual(result[0].middle, 126)
        self.assertEqual(result[0].center, 125)

    def test_decimal_rules_and_integrality(self) -> None:
        self.assertEqual(CONTRACT.parse_decimal("1"), Decimal(1))
        for invalid in ("001", "+1", "1e2", "NaN", "Infinity", "1,2", " 1"):
            with self.assertRaises(CONTRACT.ContractError):
                CONTRACT.parse_decimal(invalid)
        self.assertEqual(CONTRACT.canonical_decimal("-0.000"), "0")
        self.assertEqual(CONTRACT.canonical_decimal("12.3400"), "12.34")
        self.assertTrue(CONTRACT.exact_integral("112.000"))
        self.assertFalse(CONTRACT.exact_integral("112.5"))

    def test_ungapped_normalization_is_fail_closed(self) -> None:
        self.assertEqual(CONTRACT.normalize_ungapped(" ac-gT\n"), "ACGT")
        for invalid in ("AC GT", "AC.GT", "AC_GT", "AC~GT", "ACUGT"):
            with self.assertRaises(CONTRACT.ContractError):
                CONTRACT.normalize_ungapped(invalid)

    def test_all_reachable_coordinate_mappings_and_boundaries(self) -> None:
        target = "ACGTTGCA"
        cases = {
            "ParaPlus": (1, 1, (0, 1), "A"),
            "AntiMinus": (8, 8, (7, 8), "T"),
            "ParaMinus": (0, 0, (0, 1), "T"),
            "AntiPlus": (7, 7, (7, 8), "A"),
        }
        for strand, (raw_start, raw_end, interval, expected_tts) in cases.items():
            coordinates = CONTRACT.canonicalize_coordinates(
                raw_query_start=1,
                raw_query_end=1,
                raw_target_start=raw_start,
                raw_target_end=raw_end,
                strand=strand,
                direction="R",
                target_length=len(target),
                target_region_start0=100,
            )
            self.assertEqual((coordinates.target_start0, coordinates.target_end0), interval)
            self.assertEqual(
                (coordinates.genome_start0, coordinates.genome_end0),
                (100 + interval[0], 100 + interval[1]),
            )
            self.assertEqual(CONTRACT.reconstruct_tts(target, coordinates, strand), expected_tts)
        reverse = CONTRACT.canonicalize_coordinates(
            raw_query_start=2,
            raw_query_end=5,
            raw_target_start=2,
            raw_target_end=5,
            strand="ParaMinus",
            direction="R",
            target_length=8,
            target_region_start0=100,
        )
        self.assertEqual(CONTRACT.reconstruct_tts(target, reverse, "ParaMinus"), "CAAC")
        with self.assertRaises(CONTRACT.ContractError):
            CONTRACT.canonicalize_coordinates(
                raw_query_start=1,
                raw_query_end=1,
                raw_target_start=1,
                raw_target_end=1,
                strand="ParaPlus",
                direction="L",
                target_length=8,
                target_region_start0=0,
            )

    def test_coordinate_golden_fixture_replays_all_reachable_rows(self) -> None:
        rows = read_tsv(PAPER / "coordinate_golden_fixtures.tsv")
        reachable = [row for row in rows if row["status"] == "reachable_current_fast_path"]
        unreachable = [row for row in rows if row["status"] == "unreachable_by_current_runtime"]
        self.assertEqual({row["raw_Strand"] for row in reachable}, CONTRACT.SUPPORTED_STRANDS)
        self.assertEqual(len(unreachable), 4)
        for row in reachable:
            if row["target_sequence_inline"] == "NA":
                sequence = "".join(
                    line.strip().upper()
                    for line in (ROOT / row["target_source_path"]).read_text(encoding="ascii").splitlines()
                    if line and not line.startswith(">")
                )
            else:
                sequence = row["target_sequence_inline"]
            coordinates = CONTRACT.canonicalize_coordinates(
                raw_query_start=int(row["raw_QueryStart"]),
                raw_query_end=int(row["raw_QueryEnd"]),
                raw_target_start=int(row["raw_StartInSeq"]),
                raw_target_end=int(row["raw_EndInSeq"]),
                strand=row["raw_Strand"],
                direction=row["raw_Direction"],
                target_length=int(row["target_length"]),
                target_region_start0=int(row["target_region_start0"]),
            )
            self.assertEqual(
                (
                    coordinates.query_start0,
                    coordinates.query_end0,
                    coordinates.target_start0,
                    coordinates.target_end0,
                    coordinates.genome_start0,
                    coordinates.genome_end0,
                    CONTRACT.reconstruct_tts(sequence, coordinates, row["raw_Strand"]),
                ),
                (
                    int(row["expected_query_start0"]),
                    int(row["expected_query_end0"]),
                    int(row["expected_target_start0"]),
                    int(row["expected_target_end0"]),
                    int(row["expected_genome_start0"]),
                    int(row["expected_genome_end0"]),
                    row["expected_ungapped_tts"],
                ),
            )

    def test_input_identity_uses_and_and_namespaced_ordinals(self) -> None:
        identity = {
            field: f"value-{field}" for field in CONTRACT.INPUT_IDENTITY_FIELDS
        }
        self.assertTrue(CONTRACT.input_identity_equal(identity, dict(identity)))
        changed = dict(identity)
        changed["target_sequence_sha256"] = "different"
        self.assertFalse(CONTRACT.input_identity_equal(identity, changed))
        changed = dict(identity)
        changed["query_ordinal_namespace"] = "different_namespace"
        self.assertFalse(CONTRACT.input_identity_equal(identity, changed))
        changed = dict(identity)
        changed["assembly"] = "GRCh37"
        self.assertFalse(CONTRACT.input_identity_equal(identity, changed))

    @staticmethod
    def site(**changes):
        values = {
            "input_pair_digest": "pair",
            "chromosome_or_target_id": "target",
            "direction": "R",
            "strand": "ParaPlus",
            "rule": 1,
            "query_interval": (100, 200),
            "cluster_interval": (90, 210),
            "target_interval": (1000, 1100),
            "cluster_center": 150,
            "ungapped_tfo_sha256": "tfo",
            "ungapped_tts_sha256": "tts",
            "rank": 1,
        }
        values.update(changes)
        return CONTRACT.CandidateSite(**values)

    def test_candidate_site_edges_ignore_cigar_and_accept_three_bp_extension(self) -> None:
        left = self.site()
        right = self.site(target_interval=(997, 1103))
        edge = CONTRACT.eligible_edge(left, right)
        self.assertIsNotNone(edge)
        self.assertEqual(edge.target_overlap, Fraction(100, 106))

    def test_true_query_cluster_and_target_region_differences_do_not_match(self) -> None:
        left = self.site()
        self.assertIsNone(CONTRACT.eligible_edge(left, self.site(cluster_interval=(0, 50))))
        self.assertIsNone(CONTRACT.eligible_edge(left, self.site(target_interval=(2000, 2100))))

    def test_extra_g_site_causes_precision_failure(self) -> None:
        left = [self.site(rank=1)]
        right = [self.site(rank=1), self.site(rank=2, target_interval=(2000, 2100))]
        result = CONTRACT.match_candidate_sites(left, right)
        self.assertEqual(len(result.pairs), 1)
        self.assertNotEqual(len(result.pairs), len(right))

    def test_unique_multiple_matching_and_equivalent_ambiguity(self) -> None:
        authority = [
            self.site(rank=1, target_interval=(1000, 1100)),
            self.site(rank=2, target_interval=(2000, 2100)),
        ]
        candidate = [
            self.site(rank=1, target_interval=(1000, 1100)),
            self.site(rank=2, target_interval=(2000, 2100)),
        ]
        unique = CONTRACT.match_candidate_sites(authority, candidate)
        self.assertFalse(unique.ambiguous)
        self.assertEqual(unique.pairs, ((0, 0), (1, 1)))

        duplicate_authority = [self.site(rank=1), self.site(rank=2)]
        duplicate_candidate = [self.site(rank=1), self.site(rank=2)]
        ambiguous = CONTRACT.match_candidate_sites(duplicate_authority, duplicate_candidate)
        self.assertTrue(ambiguous.ambiguous)
        self.assertEqual(ambiguous.optimal_pair_set_count, 2)

    def test_double_empty_and_failures_use_frozen_denominator_rules(self) -> None:
        clean_empty = CONTRACT.classify_denominator(
            authority_technical_success=True,
            candidate_technical_success=True,
            input_identity_pass=True,
            authority_output_valid=True,
            candidate_output_valid=True,
            authority_candidate_count=0,
            candidate_candidate_count=0,
        )
        self.assertTrue(clean_empty.double_empty)
        self.assertFalse(clean_empty.binary_gate_denominator_eligible)
        self.assertIsNone(clean_empty.binary_success)

        a_empty_g_nonempty = CONTRACT.classify_denominator(
            authority_technical_success=True,
            candidate_technical_success=True,
            input_identity_pass=True,
            authority_output_valid=True,
            candidate_output_valid=True,
            authority_candidate_count=0,
            candidate_candidate_count=1,
        )
        self.assertFalse(a_empty_g_nonempty.informative_for_recovery)
        self.assertTrue(a_empty_g_nonempty.binary_gate_denominator_eligible)
        self.assertFalse(a_empty_g_nonempty.binary_success)

        technical = CONTRACT.classify_denominator(
            authority_technical_success=False,
            candidate_technical_success=True,
            input_identity_pass=True,
            authority_output_valid=False,
            candidate_output_valid=True,
            authority_candidate_count=None,
            candidate_candidate_count=1,
        )
        self.assertIsNone(technical.informative_for_recovery)
        self.assertTrue(technical.binary_gate_denominator_eligible)
        self.assertFalse(technical.binary_success)

    def test_clopper_pearson_fixtures(self) -> None:
        self.assertAlmostEqual(
            float(CONTRACT.clopper_pearson_lower(60, 60)),
            0.9512970866899025,
            places=15,
        )
        self.assertAlmostEqual(
            float(CONTRACT.clopper_pearson_lower(59, 60)),
            0.9233600050654955,
            places=15,
        )

    def test_exact_power_fixtures_and_boundaries(self) -> None:
        expected = {
            60: (60, "0.547156642390761"),
            89: (89, "0.408820174422549"),
            100: (99, "0.735761978922956"),
            123: (122, "0.651398441786044"),
            124: (122, "0.871553509745859"),
            150: (148, "0.809481862015847"),
        }
        for n, (minimum, approximate) in expected.items():
            actual_minimum, power = CONTRACT.exact_gate_power(n)
            self.assertEqual(actual_minimum, minimum)
            self.assertAlmostEqual(float(power), float(Decimal(approximate)), places=12)
        required_n, minimum, power = CONTRACT.required_binary_n()
        self.assertEqual((required_n, minimum), (124, 122))
        self.assertGreaterEqual(power, Decimal("0.80"))

    def test_panel_eligibility_fixture(self) -> None:
        panel_n, probability = CONTRACT.required_panel_n(124)
        self.assertEqual(panel_n, 178)
        self.assertAlmostEqual(float(probability), 0.955969707503, places=12)

    def test_finite_rbo_empty_and_exact(self) -> None:
        self.assertEqual(CONTRACT.finite_rbo([], []), 0)
        values = ["a", "b", "c", "d", "e"]
        self.assertEqual(CONTRACT.finite_rbo(values, values), 1)

    def test_contract_schema_v2_is_strict_and_supports_decimal_branch(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/biological_topk_contract.schema.json").read_text(encoding="utf-8")
        )
        contract = json.loads((PAPER / "contract_spec.json").read_text(encoding="utf-8"))
        CHECKER.validate_schema(contract, schema)
        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(contract["ranking_mode_values"], ["score", "stability", "nt"])
        self.assertEqual(
            contract["coordinate_mapping_table_sha256"],
            sha256_file(ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"),
        )

        unknown = copy.deepcopy(contract)
        unknown["matching"]["implementation_tiebreaker"] = "row_order"
        with self.assertRaises(CHECKER.SchemaValidationError):
            CHECKER.validate_schema(unknown, schema)

        decimal = copy.deepcopy(contract)
        decimal["score_representation"] = "decimal_exact"
        decimal["exact_numbers"]["score_representation"] = "decimal_exact"
        decimal["exact_numbers"]["score_integer_required"] = False
        CHECKER.validate_schema(decimal, schema)

        inconsistent = copy.deepcopy(decimal)
        inconsistent["exact_numbers"]["score_integer_required"] = True
        with self.assertRaises(CHECKER.SchemaValidationError):
            CHECKER.validate_schema(inconsistent, schema)

    def test_score_integrality_audit_and_exact_decision(self) -> None:
        audit_path = PAPER / "score_integrality_audit.tsv"
        rows = read_tsv(audit_path)
        decision = json.loads((PAPER / "score_integrality_decision.json").read_text())
        self.assertEqual(sum(int(row["row_count"]) for row in rows), 766261)
        self.assertTrue(all(row["all_integral"] == "1" for row in rows))
        self.assertTrue(all(row["nonintegral_count"] == "0" for row in rows))
        self.assertEqual(decision["decision"], "integral_exact")
        self.assertEqual(decision["audit_sha256"], sha256_file(audit_path))
        self.assertEqual(decision["supported_row_count"], 766261)

    def test_source_universe_capacity_identity_and_deterministic_gzip(self) -> None:
        receipt = json.loads((PAPER / "source_universe_receipt.json").read_text())
        query_path = PAPER / "query_source_universe.tsv.gz"
        target_path = PAPER / "target_source_universe.tsv.gz"
        self.assertEqual(query_path.read_bytes()[4:8], b"\0\0\0\0")
        self.assertEqual(target_path.read_bytes()[4:8], b"\0\0\0\0")
        self.assertEqual(receipt["query_universe"]["gzip_sha256"], sha256_file(query_path))
        self.assertEqual(receipt["target_universe"]["gzip_sha256"], sha256_file(target_path))
        with gzip.open(query_path, "rt", newline="", encoding="utf-8") as handle:
            queries = [row for row in csv.DictReader(handle, delimiter="\t") if row["historical_exclusion_status"] == "fresh_eligible"]
        with gzip.open(target_path, "rt", newline="", encoding="utf-8") as handle:
            targets = [row for row in csv.DictReader(handle, delimiter="\t") if row["historical_exclusion_status"] == "fresh_eligible"]
        self.assertGreaterEqual(len({row["sequence_sha256"] for row in queries}), 178)
        self.assertGreaterEqual(
            len({(row["query_ordinal_namespace"], row["source_ordinal"]) for row in queries}),
            178,
        )
        quotas = {"short": 60, "medium": 59, "large": 59}
        for stratum, quota in quotas.items():
            rows = [row for row in targets if row["target_scale_stratum"] == stratum]
            self.assertGreaterEqual(len({row["sequence_sha256"] for row in rows}), quota)
            self.assertGreaterEqual(
                len({(row["target_ordinal_namespace"], row["source_ordinal"]) for row in rows}),
                quota,
            )

    def test_joint_information_uses_outer_workload_bootstrap_and_precise_inner_mc(self) -> None:
        model = json.loads((PAPER / "joint_information_model.json").read_text())
        simulation = json.loads((PAPER / "joint_information_simulation.json").read_text())
        self.assertEqual(model["row_count_by_stratum"], {"large": 2, "medium": 13, "short": 48})
        tuple_fields = {
            "target_scale_stratum",
            "denominator_eligible_indicator",
            "reference_nonempty_indicator",
            "reference_candidate_site_count",
        }
        self.assertTrue(all(tuple_fields <= set(row) for row in model["planning_rows"]))
        self.assertEqual(simulation["joint_outer_bootstrap_replicates"], 2000)
        self.assertEqual(len(simulation["outer_q_distribution"]), 2000)
        self.assertEqual(sum(simulation["inner_simulation_count_distribution"].values()), 2000)
        self.assertFalse(simulation["inner_simulations_are_independent_scientific_evidence"])
        self.assertTrue(simulation["joint_inner_mc_precision_pass"])
        self.assertLessEqual(
            Decimal(simulation["inner_mc_halfwidth_max_observed"]),
            Decimal(simulation["joint_inner_mc_halfwidth_max"]),
        )
        self.assertGreaterEqual(Decimal(simulation["joint_information_probability_lcb"]), Decimal("0.95"))

    def test_resource_and_consolidated_feasibility_are_input_only_and_fail_closed(self) -> None:
        model = json.loads((PAPER / "resource_projection_model.json").read_text())
        budget = json.loads((PAPER / "fresh_budget_projection_plan.json").read_text())
        feasibility = json.loads((PAPER / "fresh_information_feasibility.json").read_text())
        sample = json.loads((PAPER / "sample_size_plan.json").read_text())
        self.assertEqual(
            model["input_features"],
            [
                "log1p_query_length",
                "log1p_target_length",
                "log1p_query_times_target",
                "query_complexity_proxy",
                "target_complexity_proxy",
                "stratum_medium",
                "stratum_large",
                "config_paper_direct_v1",
                "config_paper_sharded_v1",
            ],
        )
        self.assertEqual(model["bootstrap"]["replicates"], 10000)
        self.assertTrue(all(row["source_paths"] for row in model["historical_observations"]))
        approval = json.loads((PAPER / "owner_storage_quota_approval.json").read_text())
        self.assertEqual(approval["max_artifact_storage_bytes"], 8589934592)
        self.assertTrue(approval["phase_1_commit_replacement_authorized"])
        self.assertFalse(approval["quota_may_be_raised_after_manifest_projection"])
        self.assertEqual(budget["max_artifact_storage_bytes"], 8589934592)
        self.assertTrue(budget["artifact_storage_gate_pass"])
        self.assertTrue(budget["fixed_budget_gate_pass"])
        self.assertEqual(feasibility["phase_1_status_recommendation"], "pass")
        self.assertIsNone(feasibility["blocking_reason"])
        self.assertTrue(feasibility["gates"]["all_computable_gates_pass"])
        self.assertTrue(feasibility["gates"]["all_required_gates_pass"])
        self.assertEqual(sample["N_panel"], 178)
        self.assertEqual(sample["n_binary_required"], 124)
        self.assertEqual(sample["k_min"], 122)
        self.assertEqual(sample["joint_power_claim"], "primary_joint_information_model_frozen")
        self.assertFalse(sample["fresh_pair_selected"])
        self.assertFalse(sample["new_prediction_run"])


if __name__ == "__main__":
    unittest.main()
