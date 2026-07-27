#!/usr/bin/env python3
"""Tests for the preregistered Bioinformatics Phase 3 application runner."""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "reproduce/bioinformatics/run_application.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("phase3_application_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Phase 3 application runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeGpuSampler:
    def __init__(self, path: Path) -> None:
        self.path = path

    def start(self) -> None:
        self.path.write_text(
            "timestamp,measurement_status,gpu_index,memory_used_mib,memory_total_mib,"
            "utilization_gpu_percent,temperature_gpu_c,power_draw_w,clocks_sm_mhz\n"
            "2026-07-27T00:00:00Z,available,0,10,24564,1,30,20,210\n",
            encoding="utf-8",
        )

    def stop(self) -> None:
        return None


def schema_example(schema: dict[str, object]):
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        values = schema["enum"]
        for value in values:
            if value is not None:
                return value
        return None
    expected = schema.get("type")
    if isinstance(expected, list):
        expected = next((value for value in expected if value != "null"), "null")
    if expected == "object":
        properties = schema.get("properties", {})
        return {
            field: schema_example(properties[field])
            for field in schema.get("required", [])
        }
    if expected == "array":
        return []
    if expected == "string":
        return "x"
    if expected == "integer":
        return int(schema.get("minimum", 0))
    if expected == "number":
        return float(schema.get("minimum", 0))
    if expected == "boolean":
        return False
    if expected == "null":
        return None
    return None


def valid_report(runner, arm: str) -> dict[str, object]:
    report = schema_example(runner.RUN_REPORT_SCHEMA)
    mode, contract = runner.ARM_SPECS[arm]
    report["mode"] = mode
    report["requested_contract"] = contract
    report["resolved_contract"] = "all-ranked-top5" if contract == "all-ranked-top5" else "experimental-native"
    report["timestamps"]["wall_seconds"] = 4.0
    backend = {
        "command": ["backend"],
        "returncode": 0,
        "wall_seconds": 1.0,
        "timed_out": False,
        "peak_rss_kib": None,
        "peak_gpu_memory_mib": None,
        "start_utc": "2026-07-27T00:00:00+00:00",
        "end_utc": "2026-07-27T00:00:01+00:00",
        "stdout_tail": "",
        "stderr_tail": "",
    }
    report["comparators"] = {
        "status": "not_run",
        "returncode": None,
        "wall_seconds": None,
        "score_top5_equal": None,
        "stability_top5_equal": None,
        "nt_top5_equal": None,
        "boundary_ties_equal": None,
        "all_ranked_top5_equal": None,
        "full_rows_equal": None,
        "full_missing_rows": None,
        "full_extra_rows": None,
        "metrics": {},
    }
    report["counters"] = {"fallback": 0, "guard": 0, "oom": 0, "timeout": 0}
    if arm == "A":
        report.update(
            resolved_execution="cpu-authority",
            result_status="authority_complete",
            published_source="authority",
        )
        report["backends"] = {"authority": backend, "candidate": None}
    elif arm == "B":
        report.update(
            resolved_execution="fast-experimental",
            result_status="experimental_unverified",
            published_source="candidate",
        )
        report["backends"] = {"authority": None, "candidate": backend}
    else:
        report.update(
            mode="safe",
            resolved_execution="verified",
            result_status="candidate_clean",
            published_source="candidate",
        )
        report["backends"] = {
            "authority": {**backend, "wall_seconds": 2.0},
            "candidate": {**backend, "wall_seconds": 1.0},
        }
        report["comparators"].update(
            status="clean",
            returncode=0,
            wall_seconds=0.5,
            score_top5_equal=True,
            stability_top5_equal=True,
            nt_top5_equal=True,
            boundary_ties_equal=True,
            all_ranked_top5_equal=True,
            full_rows_equal=False,
            full_missing_rows=1,
            full_extra_rows=0,
            declared_contract_clean=True,
        )
    return report


def fake_manifest_rows(runner) -> list[dict[str, str]]:
    template = {field: "NA" for field in runner.MANIFEST_FIELDS}
    query = {
        **template,
        "record_id": "aq001",
        "record_role": "query",
        "sequence_length": "639",
        "path": "query.fa",
        "file_sha256": "1" * 64,
        "sequence_sha256": "2" * 64,
    }
    target = {
        **template,
        "record_id": "at0001",
        "record_role": "target",
        "sequence_length": "2501",
        "chromosome": "chr21",
        "path": "target.fa",
        "file_sha256": "3" * 64,
        "sequence_sha256": "4" * 64,
    }
    return [query, target]


class Phase3PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()

    def test_frozen_manifest_and_repeat_subset_are_exact(self) -> None:
        rows = self.runner.load_application_manifest()
        subset = self.runner.expected_subset_rows(rows)
        queries = [row for row in subset if row["record_role"] == "query"]
        targets = [row for row in subset if row["record_role"] == "target"]
        self.assertEqual((len(rows), len(queries), len(targets)), (718, 10, 20))
        self.assertEqual(len({row["record_id"] for row in subset}), 30)
        self.assertEqual(
            {row["chromosome"] for row in targets}, {"chr21", "chr22"}
        )
        self.assertEqual(
            [int(row["sequence_length"]) for row in queries],
            sorted(int(row["sequence_length"]) for row in queries),
        )
        self.assertEqual(subset, self.runner.expected_subset_rows(list(reversed(rows))))

    def test_attempt_plan_has_fixed_pilot_full_and_balanced_repeats(self) -> None:
        rows = self.runner.expected_plan_rows("a" * 40, "b" * 64)
        self.assertEqual(len(rows), 24)
        pilot = [row for row in rows if row["execution_stage"] == "pilot"]
        full = [row for row in rows if row["execution_stage"] == "formal_full"]
        repeats = [row for row in rows if row["execution_stage"] == "formal_repeat"]
        self.assertEqual((len(pilot), len(full), len(repeats)), (3, 3, 18))
        self.assertEqual([row["arm"] for row in pilot], ["A", "B", "C"])
        self.assertTrue(all(row["scope"] == "aq001_at0001" for row in pilot))
        self.assertTrue(all(row["formal_source_data"] == 0 for row in pilot))
        self.assertTrue(all(row["scope"] == "50x668" for row in full))
        by_repeat = {
            repeat: [
                row["arm"]
                for row in repeats
                if row["repeat_id"] == repeat
            ]
            for repeat in range(6)
        }
        self.assertEqual(by_repeat[0], ["A", "B", "C"])
        self.assertEqual(by_repeat[1], ["C", "B", "A"])
        self.assertTrue(all(row["retry_policy"] == "none" for row in rows))
        self.assertTrue(all(row["worker_count"] == 2 for row in rows))

    def test_preexecution_decision_preserves_structural_no_go(self) -> None:
        decision = self.runner.expected_preexecution_decision(
            runner_commit="a" * 40,
            runner_sha256="b" * 64,
            plan_sha256="c" * 64,
            subset_sha256="d" * 64,
        )
        self.assertEqual(decision["phase2_decision"], "verified_only_contract")
        self.assertFalse(decision["b3_threshold_changed"])
        self.assertEqual(decision["b3_safe_speedup_threshold"], 10.0)
        self.assertEqual(
            decision["b3_promotion_feasibility"],
            "structurally_unreachable_under_verified_only_v1",
        )
        self.assertFalse(decision["pilot_can_promote_b3"])
        self.assertFalse(decision["candidate_only_can_be_reported_as_safe_acceleration"])
        self.assertNotIn(
            "continue_for_b3_promotion", decision["allowed_post_pilot_decisions"]
        )
        self.assertEqual(
            decision["postpilot_decision_precedence"],
            [
                "blocked_by_operational_failure",
                "blocked_by_fixed_budget",
                "stop_after_pilot_futility",
            ],
        )
        self.assertTrue(
            decision["continue_full_descriptive_negative_requires_owner_authorization"]
        )
        self.assertEqual(
            tuple(decision["allowed_post_pilot_decisions"]),
            self.runner.ALLOWED_POST_PILOT_DECISIONS,
        )

    def test_postpilot_decision_order_is_fixed_before_execution(self) -> None:
        attempts = [
            {
                "arm": arm,
                "outcome": "complete",
                "technical_failure_count": 0,
                "timeout_count": 0,
                "oom_count": 0,
            }
            for arm in ("A", "B", "C")
        ]
        self.assertEqual(
            self.runner.select_postpilot_decision(
                attempts, {"within_fixed_budget": True}
            ),
            "stop_after_pilot_futility",
        )
        self.assertEqual(
            self.runner.select_postpilot_decision(
                attempts, {"within_fixed_budget": False}
            ),
            "blocked_by_fixed_budget",
        )
        failed = json.loads(json.dumps(attempts))
        failed[1]["technical_failure_count"] = 1
        self.assertEqual(
            self.runner.select_postpilot_decision(
                failed, {"within_fixed_budget": False}
            ),
            "blocked_by_operational_failure",
        )

    def test_checked_in_plan_round_trips_when_present(self) -> None:
        if not self.runner.PLAN_PATH.is_file():
            self.skipTest("attempt plan is generated only after the runner source commit")
        rows, decision = self.runner.load_and_validate_plan()
        self.assertEqual(len(rows), 24)
        self.assertEqual(decision["full_run_decision"], "pending_fixed_pilot")
        summary = self.runner.plan_summary()
        self.assertEqual(summary["attempt_counts_by_stage"]["pilot"], 3)
        self.assertFalse(summary["application_execution_started"])


class Phase3ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_each_arm_report_contract_is_independently_validated(self) -> None:
        for arm in ("A", "B", "C"):
            with self.subTest(arm=arm):
                mode, contract = self.runner.ARM_SPECS[arm]
                row = {"arm": arm, "mode": mode, "contract": contract}
                path = self.work / f"{arm}.json"
                path.write_text(
                    json.dumps(valid_report(self.runner, arm)), encoding="utf-8"
                )
                report = self.runner.read_and_validate_report(path, row)
                self.assertEqual(report["mode"], mode)

    def test_safe_c_requires_candidate_complete_authority_and_comparison(self) -> None:
        report = valid_report(self.runner, "C")
        row = {"arm": "C", "mode": "safe", "contract": "all-ranked-top5"}
        mutations = (
            ("candidate", lambda value: value["backends"].__setitem__("candidate", None)),
            ("authority", lambda value: value["backends"].__setitem__("authority", None)),
            ("comparison", lambda value: value["comparators"].__setitem__("status", "not_run")),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = json.loads(json.dumps(report))
                mutate(changed)
                path = self.work / f"bad-{label}.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.runner.read_and_validate_report(path, row)

    def test_component_timing_exposes_verified_additive_cost(self) -> None:
        report = valid_report(self.runner, "C")
        timing = self.runner.component_timings(report, 4.0)
        self.assertEqual(timing["candidate_wall_seconds"], 1.0)
        self.assertEqual(timing["authority_wall_seconds"], 2.0)
        self.assertEqual(timing["comparison_wall_seconds"], 0.5)
        self.assertEqual(timing["component_wall_seconds_sum"], 3.5)
        self.assertEqual(timing["runner_and_wrapper_overhead_seconds"], 0.5)

    def test_workflow_command_preserves_literal_paths_without_shell(self) -> None:
        tools = self.runner.ToolPaths(
            workflow=self.work / "workflow ; literal.py",
            comparator=self.work / "compare $(literal).py",
            authority_binary=self.work / "authority [literal]",
            candidate_binary=self.work / "candidate & literal",
        )
        row = {"mode": "safe", "contract": "all-ranked-top5"}
        query = self.work / "query ; $(touch NEVER).fa"
        target = self.work / "target [literal].fa"
        command = self.runner.workflow_command(row, query, target, self.work, tools)
        self.assertIsInstance(command, list)
        self.assertIn(str(query.resolve()), command)
        self.assertIn(str(target.resolve()), command)
        self.assertNotIn("sh", command[:1])

    def test_real_pair_executor_captures_valid_safe_components(self) -> None:
        fake_root = self.work / "repo with spaces;literal"
        fake_root.mkdir()
        query = fake_root / "query.fa"
        target = fake_root / "target.fa"
        query.write_text(">q\nACGT\n", encoding="ascii")
        target.write_text(">t\nACGT\n", encoding="ascii")
        report_source = fake_root / "safe-report.json"
        report_source.write_text(
            json.dumps(valid_report(self.runner, "C")), encoding="utf-8"
        )
        workflow = fake_root / "fake workflow.py"
        workflow.write_text(
            """#!/usr/bin/env python3
import argparse
import os
import shutil
from pathlib import Path

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--report', required=True)
parser.add_argument('--output', required=True)
args, _ = parser.parse_known_args()
Path(args.output).mkdir(parents=True)
(Path(args.output) / 'result.tsv').write_text('ok\\n', encoding='utf-8')
shutil.copyfile(os.environ['FAKE_REPORT_SOURCE'], args.report)
""",
            encoding="utf-8",
        )
        dummy = fake_root / "dummy"
        dummy.write_text("dummy\n", encoding="utf-8")
        attempt_dir = fake_root / "attempt"
        attempt_dir.mkdir()
        row = {
            "attempt_id": "p3pilot_c_aq001_at0001",
            "arm": "C",
            "mode": "safe",
            "contract": "all-ranked-top5",
        }
        query_row = {
            "record_id": "aq001",
            "path": "query.fa",
            "file_sha256": "1" * 64,
        }
        target_row = {
            "record_id": "at0001",
            "path": "target.fa",
            "file_sha256": "2" * 64,
        }
        tools = self.runner.ToolPaths(
            workflow=workflow,
            comparator=dummy,
            authority_binary=dummy,
            candidate_binary=dummy,
        )
        with mock.patch.object(self.runner, "ROOT", fake_root), mock.patch.dict(
            os.environ, {"FAKE_REPORT_SOURCE": str(report_source)}
        ):
            result = self.runner.run_pair(
                row=row,
                pair_index=0,
                query_row=query_row,
                target_row=target_row,
                worker_id=0,
                attempt_dir=attempt_dir,
                tools=tools,
            )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["candidate_wall_seconds"], 1.0)
        self.assertEqual(result["authority_wall_seconds"], 2.0)
        self.assertEqual(result["comparison_wall_seconds"], 0.5)
        pair_dir = attempt_dir / "pairs" / result["pair_id"]
        self.assertTrue((pair_dir / "artifact_manifest.sha256").is_file())


class Phase3AttemptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifact_root = self.root / "artifacts"
        self.rows = fake_manifest_rows(self.runner)
        plan_row = self.runner.expected_plan_rows("a" * 40, "b" * 64)[0]
        self.row = {field: str(value) for field, value in plan_row.items()}
        self.identity = {
            "attempt_plan_sha256": "c" * 64,
            "identity_sha256": "d" * 64,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def fake_pair_executor(**kwargs) -> dict[str, object]:
        row = kwargs["row"]
        pair_index = kwargs["pair_index"]
        query = kwargs["query_row"]
        target = kwargs["target_row"]
        worker = kwargs["worker_id"]
        pair_id = f"pair{pair_index:05d}_{query['record_id']}_{target['record_id']}"
        pair_dir = kwargs["attempt_dir"] / "pairs" / pair_id
        pair_dir.mkdir(parents=True)
        (pair_dir / "stdout.log").write_text("ok\n", encoding="utf-8")
        (pair_dir / "stderr.log").write_text("", encoding="utf-8")
        (pair_dir / "run-report.json").write_text("{}\n", encoding="utf-8")
        runner = sys.modules["phase3_application_runner"]
        manifest_sha, count = runner.write_artifact_manifest(pair_dir)
        return {
            "pair_id": pair_id,
            "pair_index": pair_index,
            "query_id": query["record_id"],
            "target_id": target["record_id"],
            "worker_id": worker,
            "physical_gpu": worker,
            "returncode": 0,
            "timed_out": False,
            "report_schema_valid": True,
            "report_validation_error": None,
            "result_status": "authority_complete",
            "fallback_count": 0,
            "oom_count": 0,
            "timeout_count": 0,
            "published_backend": "authority",
            "contract_result": None,
            "total_wall_seconds": 1.0,
            "candidate_wall_seconds": None,
            "authority_wall_seconds": 0.8,
            "comparison_wall_seconds": None,
            "artifact_manifest_sha256": manifest_sha,
            "artifact_count": count,
            "status": "complete",
        }

    def execute(self, *, resume: bool = False, executor=None):
        executor = executor or self.fake_pair_executor
        with mock.patch.object(self.runner, "GpuSampler", FakeGpuSampler), mock.patch.object(
            self.runner, "validate_execution_identity", lambda *_args: None
        ), mock.patch.dict(os.environ, {"PHASE3_APPLICATION_TEST_MODE": "1"}):
            return self.runner.execute_attempt(
                row=self.row,
                manifest_rows=self.rows,
                subset_rows=[],
                identity=self.identity,
                tools=self.runner.ToolPaths(),
                artifact_root=self.artifact_root,
                resume=resume,
                pair_executor=executor,
            )

    def test_attempt_is_immutable_and_resume_only_reuses_valid_receipt(self) -> None:
        result = self.execute()
        self.assertEqual(result["status"], "executed")
        destination = self.artifact_root / "pilot" / self.row["attempt_id"]
        self.assertTrue((destination / "attempt-complete.json").is_file())
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.execute()
        reused = self.execute(resume=True)
        self.assertEqual(reused["status"], "reused")

    def test_incomplete_attempt_is_preserved_and_never_resumed(self) -> None:
        destination = self.artifact_root / "pilot" / self.row["attempt_id"]
        destination.mkdir(parents=True)
        (destination / "attempt.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "receipt is missing"):
            self.execute(resume=True)
        self.assertTrue((destination / "attempt.json").is_file())

    def test_technical_failure_receipt_is_retained(self) -> None:
        def failed(**kwargs):
            result = self.fake_pair_executor(**kwargs)
            result.update(
                returncode=7,
                report_schema_valid=False,
                report_validation_error="invalid report",
                status="technical_failure",
            )
            return result

        result = self.execute(executor=failed)
        self.assertEqual(result["receipt"]["outcome"], "technical_failure")
        destination = self.artifact_root / "pilot" / self.row["attempt_id"]
        self.assertTrue((destination / "attempt-complete.json").is_file())

    def test_artifact_tampering_invalidates_resume_receipt(self) -> None:
        self.execute()
        destination = self.artifact_root / "pilot" / self.row["attempt_id"]
        (destination / "stdout.log").write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "(?:size|digest) drift"):
            self.runner.validate_attempt_receipt(destination, self.row["attempt_id"])

    def test_unlisted_artifact_invalidates_resume_receipt(self) -> None:
        self.execute()
        destination = self.artifact_root / "pilot" / self.row["attempt_id"]
        (destination / "unlisted.txt").write_text("unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "file set drift"):
            self.runner.validate_attempt_receipt(destination, self.row["attempt_id"])

    def test_formal_budget_receipt_is_fixed_and_identity_bound(self) -> None:
        identity = {
            "attempt_plan_sha256": "a" * 64,
            "git_head": "b" * 40,
        }
        deadline = self.runner.formal_budget_deadline(self.artifact_root, identity)
        self.assertGreater(deadline, 0)
        payload = json.loads(
            (self.artifact_root / "formal-budget.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["budget_seconds"], 86400)
        self.assertEqual(payload["retry_policy"], "none")
        self.assertEqual(
            self.runner.formal_budget_deadline(self.artifact_root, identity), deadline
        )
        with self.assertRaisesRegex(ValueError, "plan drift"):
            self.runner.formal_budget_deadline(
                self.artifact_root,
                {"attempt_plan_sha256": "c" * 64, "git_head": "b" * 40},
            )


class Phase3RepositoryIntegrationTests(unittest.TestCase):
    def test_make_target_and_checker_are_present(self) -> None:
        checker = ROOT / "scripts/check_bioinformatics_phase3_preexecution.sh"
        self.assertTrue(checker.is_file())
        text = checker.read_text(encoding="utf-8")
        for phrase in (
            "application_attempt_plan.tsv",
            "phase3_preexecution_decision.json",
            "check_run_bioinformatics_application.py",
            "application_execution_started=0",
            "structurally_unreachable_under_verified_only_v1",
            "cd \"$ROOT/paper/bioinformatics\"",
        ):
            self.assertIn(phrase, text)
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("check-bioinformatics-phase3-preexecution:", makefile)
        self.assertIn("check_bioinformatics_phase3_preexecution.sh", makefile)

    def test_submission_manifest_tracks_preexecution_layer(self) -> None:
        if not (ROOT / "paper/bioinformatics/application_attempt_plan.tsv").is_file():
            self.skipTest("submission rows are frozen with the post-runner attempt plan")
        path = ROOT / "paper/bioinformatics/submission_manifest.tsv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        by_path = {row["path"]: row for row in rows}
        expected = {
            "paper/bioinformatics/application_attempt_plan.tsv",
            "paper/bioinformatics/application_attempt_plan.sha256",
            "paper/bioinformatics/application_repeat_subset.tsv",
            "paper/bioinformatics/phase3_preexecution_decision.json",
            "reproduce/bioinformatics/run_application.py",
            "scripts/check_bioinformatics_phase3_preexecution.sh",
            "tests/check_run_bioinformatics_application.py",
        }
        self.assertTrue(expected <= set(by_path), sorted(expected - set(by_path)))
        self.assertTrue(all(by_path[item]["phase"] == "3" for item in expected))
        self.assertTrue(all(by_path[item]["status"] == "pass" for item in expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
