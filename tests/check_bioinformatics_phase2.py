#!/usr/bin/env python3
from __future__ import annotations

import copy
import csv
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "reproduce/bioinformatics/analyze_holdout_results.py"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class Phase2CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("analyze_holdout_results", ANALYZER)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load Phase 2 analyzer")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.schema = json.loads((ROOT / "schemas/gasal2_longtarget_contracts.schema.json").read_text())
        cls.registry = json.loads((ROOT / "config/gasal2_longtarget_contracts.json").read_text())

    def test_registry_is_exact_post_holdout_verified_only_state(self) -> None:
        self.module.validate_contract_registry_data(self.schema, self.registry)
        self.assertEqual(self.registry["schema_version"], "2.0.0")
        self.assertEqual(self.registry["registry_state"], "post_holdout_decision")
        self.assertEqual(self.registry["phase2_decision"], "verified_only_contract")
        self.assertEqual(self.registry["safe_resolution"]["strategy"], "verified_or_authority")
        self.assertFalse(self.registry["safe_resolution"]["gpu_only_contract_promoted"])
        self.assertEqual(self.registry["holdout_results"]["status"], "complete_with_results")
        contracts = {row["contract_id"]: row for row in self.registry["contracts"]}
        self.assertEqual(set(contracts), {"score_top5_v1", "all_ranked_top5_v1", "full_output_v1"})
        self.assertTrue(all(row["status"] == "experimental" for row in contracts.values()))
        self.assertEqual(contracts["score_top5_v1"]["clean_mismatch_counts"]["holdout"]["clean"], 23)
        self.assertEqual(contracts["score_top5_v1"]["clean_mismatch_counts"]["holdout"]["mismatch"], 1)
        self.assertEqual(contracts["all_ranked_top5_v1"]["clean_mismatch_counts"]["holdout"]["clean"], 22)
        self.assertEqual(contracts["full_output_v1"]["clean_mismatch_counts"]["holdout"]["clean"], 20)

    def test_schema_validator_rejects_invalid_post_holdout_combinations(self) -> None:
        mutations = {
            "wrong_decision": lambda value: value.update(phase2_decision="score_top5_gpu_only"),
            "promoted_status": lambda value: value["contracts"][0].update(status="promoted"),
            "null_count": lambda value: value["contracts"][0]["clean_mismatch_counts"]["holdout"].update(clean=None),
            "false_zero_mismatch": lambda value: value["contracts"][0]["clean_mismatch_counts"]["holdout"].update(clean=24, mismatch=0),
            "unsafe_resolution": lambda value: value["safe_resolution"].update(strategy="gpu_only"),
            "pre_holdout_dataset": lambda value: value["contracts"][0]["validation_datasets"][1].update(status="preregistered_not_run"),
            "query_allowlist": lambda value: value["contracts"][0]["input_guards"].update(query_ids=["hq01"]),
            "digest_allowlist": lambda value: value["safe_resolution"].update(digests=["0" * 64]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                value = copy.deepcopy(self.registry)
                mutate(value)
                with self.assertRaises(ValueError):
                    self.module.validate_contract_registry_data(self.schema, value)

    def test_registry_contains_no_identifier_digest_or_result_allowlist(self) -> None:
        forbidden_keys = {"query_ids", "gene_names", "target_ids", "digests", "result_allowlist", "blacklist", "mechanism_guard"}

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys.intersection(value))
                for key, child in value.items():
                    self.assertNotIn("allowlist", key.lower())
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.registry)

    def test_final_decision_docs_and_claim_ledger_are_narrow(self) -> None:
        summary = json.loads((ROOT / "paper/bioinformatics/holdout_summary.json").read_text())
        self.assertEqual(summary["decision"], "verified_only_contract")
        self.assertEqual(
            summary["guard_coverage"],
            {
                "mechanism_guard_inferred": False,
                "gpu_only_promoted": {"covered_workloads": 0, "total_workloads": 24},
                "safe_verified_or_authority_contract_safe": {
                    "covered_workloads": 24,
                    "total_workloads": 24,
                },
            },
        )
        decision = (ROOT / "paper/bioinformatics/phase2_decision.md").read_text()
        for phrase in (
            "35/36 attempts", "23/24 workloads", "hq10_ht02", "hq11_ht02",
            "No GPU-only safe contract is promoted", "Safe execution continues",
            "fixed pilot receipt", "excluded from the formal analysis basis",
            "GPU-only promoted coverage is 0/24 workloads",
            "verified-or-authority contract-safe coverage is 24/24 workloads",
            "No mechanism guard was inferred",
        ):
            self.assertIn(phrase, decision)
        claim = next(row for row in read_tsv(ROOT / "paper/bioinformatics/claim_evidence.tsv") if row["claim_id"] == "B2")
        self.assertEqual(claim["status"], "pass")
        self.assertIn("verified", claim["allowed_wording"].lower())
        self.assertIn("authority", claim["allowed_wording"].lower())
        self.assertNotIn("promoted fast path", claim["allowed_wording"].lower())
        for phrase in (
            "old frozen n=13",
            "holdout n=24",
            "development score clean/mismatch 13/0",
            "development stability clean/mismatch 11/2",
            "development Nt clean/mismatch 12/1",
            "holdout score clean/mismatch 23/1",
            "holdout stability clean/mismatch 23/1",
            "holdout Nt clean/mismatch 24/0",
            "no mechanism guard inferred",
            "GPU-only promoted coverage 0/24",
            "safe verified-or-authority contract-safe coverage 24/24",
            "3 verified fallbacks",
            "36/36 boundary ties",
            "non-promoted stability, Nt, and full-row limitations",
        ):
            self.assertIn(phrase, claim["required_evidence"])
        for source in (
            "paper/bioinformatics/frozen_contract_matrix.tsv",
            "paper/bioinformatics/mismatch_analysis.md",
            "config/gasal2_longtarget_contracts.json",
            "paper/bioinformatics/holdout_summary.json",
            "paper/bioinformatics/holdout_rank_results.tsv",
            "paper/bioinformatics/holdout_workload_results.tsv",
            "paper/bioinformatics/phase2_decision.md",
        ):
            self.assertIn(source, claim["authoritative_source"])

    def test_user_docs_state_final_verified_only_routing(self) -> None:
        readme = (ROOT / "README.md").read_text()
        cli = (ROOT / "docs/gasal2_longtarget_cli.md").read_text()
        for text in (readme, cli):
            self.assertIn("verified-only", text.lower())
            self.assertIn("verified", text)
            self.assertIn("CPU authority", text)
            self.assertNotIn("Before a contract is promoted", text)
            self.assertNotIn("Before Phase 2 promotion", text)
            self.assertNotIn("Phase 2 may introduce", text)
        receipt = (ROOT / "paper/bioinformatics/README.md").read_text()
        self.assertIn("## Phase 2 receipt", receipt)
        self.assertIn("verified_only_contract", receipt)

    def test_submission_manifest_enumerates_all_final_phase2_artifacts(self) -> None:
        manifest = read_tsv(ROOT / "paper/bioinformatics/submission_manifest.tsv")
        paths = {row["path"] for row in manifest if row["phase"] == "2"}
        expected = {
            "reproduce/bioinformatics/analyze_holdout_results.py",
            "tests/check_analyze_bioinformatics_phase2.py",
            "tests/check_bioinformatics_phase2.py",
            "scripts/check_bioinformatics_phase2.sh",
            "paper/bioinformatics/holdout_attempt_results.tsv",
            "paper/bioinformatics/holdout_workload_results.tsv",
            "paper/bioinformatics/holdout_rank_results.tsv",
            "paper/bioinformatics/holdout_mode_results.tsv",
            "paper/bioinformatics/holdout_mismatch_details.tsv",
            "paper/bioinformatics/holdout_raw_artifacts.tsv",
            "paper/bioinformatics/holdout_summary.json",
            "paper/bioinformatics/phase2_decision.md",
        }
        self.assertTrue(expected.issubset(paths))
        self.assertTrue(all(row["status"] == "pass" for row in manifest if row["path"] in expected))
        schema_row = next(row for row in manifest if row["artifact_id"] == "S0202")
        self.assertEqual(schema_row["freeze_or_epoch"], "schema_2.0.0")

    def test_goal_state_preserves_phase2_after_phase3_decision(self) -> None:
        goal = (ROOT / "goal-bioinformatics.md").read_text()
        for phrase in (
            "active_phase = 4",
            "phase_2_status = pass",
            "phase_3_status = no_go",
            "last_completed_phase = 3",
            "last_decision = stop_after_pilot_futility",
            "last_evidence_doc = paper/bioinformatics/phase3_postpilot_decision.json",
            "last_test_command = make check-bioinformatics-phase3-pilot",
            "last_commit = bench: record Phase 3 fixed-pilot futility stop",
        ):
            self.assertIn(phrase, goal)
        decision = (ROOT / "paper/bioinformatics/phase2_decision.md").read_text()
        self.assertIn("`verified_only_contract`", decision)

    def test_final_checker_and_make_target_are_wired_without_execution_runner(self) -> None:
        checker_path = ROOT / "scripts/check_bioinformatics_phase2.sh"
        self.assertTrue(checker_path.is_file())
        checker = checker_path.read_text()
        for phrase in (
            "check_analyze_bioinformatics_phase2.py",
            "check_bioinformatics_phase2.py",
            "check_analyze_bioinformatics_frozen_contracts.py",
            "check_gasal2_longtarget_cli.py",
            "analyze_holdout_results.py",
            "diff --quiet",
        ):
            self.assertIn(phrase, checker)
        for forbidden in ("check_bioinformatics_phase2_preexecution.sh", "run_holdout.py --pilot", "run_holdout.py --formal"):
            self.assertNotIn(forbidden, checker)
        self.assertNotIn("check-fasim-gasal2-paper-prep", checker)
        for phrase in (
            "check_fasim_gasal2_paper_reproduction.py",
            "check_audit_fasim_gasal2_paper_results.py",
            "reproduce/check_reproduction.sh",
            "merge-base --is-ancestor",
        ):
            self.assertIn(phrase, checker)
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("check-bioinformatics-phase2:\n", makefile)
        self.assertIn("bash ./scripts/check_bioinformatics_phase2.sh", makefile)


if __name__ == "__main__":
    unittest.main()
