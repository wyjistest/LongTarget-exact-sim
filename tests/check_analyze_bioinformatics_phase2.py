#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "reproduce/bioinformatics/analyze_holdout_results.py"
FROZEN_ROOT = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
OUTPUT_NAMES = (
    "holdout_attempt_results.tsv",
    "holdout_workload_results.tsv",
    "holdout_rank_results.tsv",
    "holdout_mode_results.tsv",
    "holdout_mismatch_details.tsv",
    "holdout_raw_artifacts.tsv",
    "holdout_summary.json",
    "phase2_decision.md",
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def fingerprint_tree_no_follow(root: Path) -> str:
    digest = hashlib.sha256()

    def visit(path: Path, relative: str) -> None:
        metadata = path.lstat()
        digest.update(f"{relative}\0{metadata.st_mode:o}\0{metadata.st_size}\0".encode())
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode())
        elif path.is_dir():
            digest.update(b"directory\0")
            for child in sorted(path.iterdir(), key=lambda item: item.name):
                visit(child, f"{relative}/{child.name}")
        elif path.is_file():
            digest.update(b"file\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        else:
            digest.update(b"nonregular\0")

    visit(root, ".")
    return digest.hexdigest()


def hardlink_copytree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, copy_function=os.link)
    for path in [destination, *(item for item in destination.rglob("*") if item.is_dir())]:
        os.chmod(path, path.stat().st_mode | 0o700)


def replace_copy(path: Path, payload: bytes) -> None:
    original_mode = path.stat().st_mode
    path.unlink()
    path.write_bytes(payload)
    os.chmod(path, original_mode)


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def replace_json(path: Path, payload: object) -> None:
    replace_copy(path, canonical_json_bytes(payload))


def render_tsv(fieldnames: list[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def reseal_attempt(root: Path, attempt_id: str) -> None:
    attempt = root / "formal" / attempt_id
    artifact_rows = []
    for path in sorted(item for item in attempt.rglob("*") if item.is_file()):
        relative = path.relative_to(attempt).as_posix()
        if relative in {"attempt-artifacts.tsv", "attempt-complete.json"}:
            continue
        artifact_rows.append({
            "artifact_path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    attempt_manifest = attempt / "attempt-artifacts.tsv"
    replace_copy(
        attempt_manifest,
        render_tsv(["artifact_path", "size_bytes", "sha256"], artifact_rows),
    )
    config = json.loads((attempt / "attempt-config.json").read_text())
    summary_path = attempt / "attempt-summary.json"
    receipt_path = attempt / "attempt-complete.json"
    receipt = json.loads(receipt_path.read_text())
    receipt.update(
        artifact_count=len(artifact_rows),
        artifact_manifest_sha256=hashlib.sha256(attempt_manifest.read_bytes()).hexdigest(),
        config_digest_sha256=config["config_digest_sha256"],
        config_sha256=hashlib.sha256((attempt / "attempt-config.json").read_bytes()).hexdigest(),
        summary_sha256=hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    )
    replace_json(receipt_path, receipt)

    root_artifacts_path = root / "formal-artifacts.tsv"
    root_artifacts = read_tsv(root_artifacts_path)
    indices = [index for index, row in enumerate(root_artifacts) if row["attempt_id"] == attempt_id]
    if not indices:
        raise AssertionError(f"attempt absent from root artifact table: {attempt_id}")
    replacement = [
        {
            "attempt_id": attempt_id,
            "artifact_path": f"formal/{attempt_id}/{row['artifact_path']}",
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
        }
        for row in artifact_rows
    ]
    for name in ("attempt-artifacts.tsv", "attempt-complete.json"):
        path = attempt / name
        replacement.append({
            "attempt_id": attempt_id,
            "artifact_path": f"formal/{attempt_id}/{name}",
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    root_artifacts[indices[0] : indices[-1] + 1] = replacement
    replace_copy(
        root_artifacts_path,
        render_tsv(["attempt_id", "artifact_path", "size_bytes", "sha256"], root_artifacts),
    )

    attempts_path = root / "formal-attempts.tsv"
    attempt_rows = read_tsv(attempts_path)
    row = next(item for item in attempt_rows if item["attempt_id"] == attempt_id)
    row["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    row["config_digest_sha256"] = config["config_digest_sha256"]
    replace_copy(
        attempts_path,
        render_tsv(list(attempt_rows[0]), attempt_rows),
    )


class AnalyzerPresenceTests(unittest.TestCase):
    def test_generator_exists(self) -> None:
        self.assertTrue(GENERATOR.is_file(), "Phase 2 holdout analyzer is missing")


@unittest.skipUnless(GENERATOR.is_file(), "Phase 2 holdout analyzer is missing")
class AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("analyze_holdout_results", GENERATOR)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load Phase 2 holdout analyzer")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.temp = tempfile.TemporaryDirectory(prefix="phase2-analysis-")
        cls.output = Path(cls.temp.name) / "output"
        cls.analyze_calls: list[str] = []
        real_loader = cls.module._load_comparator

        def recording_loader(repo_root: Path):
            real_analyze = real_loader(repo_root)

            def recording_analyze(path: Path, k: int, distance: int, length: int):
                cls.analyze_calls.append(path.as_posix())
                return real_analyze(path, k, distance, length)

            return recording_analyze

        cls.module._load_comparator = recording_loader
        try:
            cls.module.generate(ROOT, cls.output)
        finally:
            cls.module._load_comparator = real_loader

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_exact_result_cardinalities_and_decision(self) -> None:
        attempts = read_tsv(self.output / "holdout_attempt_results.tsv")
        workloads = read_tsv(self.output / "holdout_workload_results.tsv")
        ranks = read_tsv(self.output / "holdout_rank_results.tsv")
        modes = read_tsv(self.output / "holdout_mode_results.tsv")
        details = read_tsv(self.output / "holdout_mismatch_details.tsv")
        summary = json.loads((self.output / "holdout_summary.json").read_text())

        self.assertEqual(len(attempts), 36)
        self.assertEqual(len(workloads), 24)
        self.assertEqual(len(ranks), 108)
        self.assertEqual(len(modes), 108)
        self.assertGreater(len(details), 0)
        self.assertEqual(summary["decision"], "verified_only_contract")
        self.assertEqual(summary["attempt_counts"]["scientific_mismatch"], 2)
        self.assertEqual(summary["attempt_counts"]["verified_fallback"], 3)
        self.assertEqual(summary["attempt_rank_counts"]["score"], {"clean": 35, "mismatch": 1})
        self.assertEqual(summary["attempt_rank_counts"]["stability"], {"clean": 35, "mismatch": 1})
        self.assertEqual(summary["attempt_rank_counts"]["nt"], {"clean": 36, "mismatch": 0})
        self.assertEqual(summary["workload_rank_counts"]["score"], {"clean": 23, "mismatch": 1})
        self.assertEqual(summary["workload_rank_counts"]["stability"], {"clean": 23, "mismatch": 1})
        self.assertEqual(summary["workload_rank_counts"]["nt"], {"clean": 24, "mismatch": 0})
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
        self.assertEqual(
            {(row["attempt_id"], row["rank"]) for row in ranks if row["rank_equal"] == "0"},
            {("hq10_ht02__repeat00", "stability"), ("hq11_ht02__repeat00", "score")},
        )

    def test_recomputes_every_direct_authority_and_candidate_output(self) -> None:
        direct_calls = [path for path in self.analyze_calls if "/authority/output/" in path or "/candidate/output/" in path]
        self.assertEqual(len(direct_calls), 72)
        self.assertEqual(len(set(direct_calls)), 72)

    def test_fallback_publications_are_authority_bytes(self) -> None:
        attempts = read_tsv(self.output / "holdout_attempt_results.tsv")
        fallback_ids = {row["attempt_id"] for row in attempts if row["verified_fallback"] == "1"}
        self.assertEqual(
            fallback_ids,
            {"hq10_ht02__repeat00", "hq11_ht02__repeat00", "hq12_ht02__repeat00"},
        )
        for attempt_id in fallback_ids:
            attempt = FROZEN_ROOT / "formal" / attempt_id
            authority = next((attempt / "authority/output").glob("*-TFOsorted"))
            verified = next((attempt / "verified/output").glob("*-TFOsorted"))
            self.assertEqual(authority.read_bytes(), verified.read_bytes())

    def test_preregistered_repeats_have_consistent_contract_signatures(self) -> None:
        workloads = read_tsv(self.output / "holdout_workload_results.tsv")
        repeated = [row for row in workloads if row["repeat_count"] == "3"]
        self.assertEqual({row["workload_id"] for row in repeated}, {
            "hq01_ht01", "hq01_ht02", "hq05_ht01", "hq05_ht02", "hq09_ht01", "hq09_ht02",
        })
        self.assertTrue(all(row["repeat_contract_consistent"] == "1" for row in repeated))
        self.assertTrue(all(row["repeat_top5_signatures_consistent"] == "1" for row in repeated))

    def test_generation_is_byte_stable_against_checked_in_outputs(self) -> None:
        checked_in = ROOT / "paper/bioinformatics"
        for name in OUTPUT_NAMES:
            self.assertEqual(
                (checked_in / name).read_bytes(),
                (self.output / name).read_bytes(),
                f"generated output drift: {name}",
            )

    def test_frozen_tree_was_not_mutated(self) -> None:
        before = digest_tree(FROZEN_ROOT)
        with tempfile.TemporaryDirectory(prefix="phase2-regenerate-") as temp_name:
            self.module.generate(ROOT, Path(temp_name) / "output")
        self.assertEqual(digest_tree(FROZEN_ROOT), before)

    def assert_overlap_rejected_without_mutation(
        self,
        sandbox: Path,
        clone: Path,
        output: Path,
    ) -> None:
        before = fingerprint_tree_no_follow(sandbox)
        error: ValueError | None = None
        try:
            self.module.generate(ROOT, output, artifact_root=clone)
        except ValueError as exc:
            error = exc
        self.assertEqual(fingerprint_tree_no_follow(sandbox), before)
        self.assertIsNotNone(error, "overlapping output/artifact roots were accepted")
        self.assertRegex(str(error), "overlap|disjoint|containment")
        self.assertEqual(list(sandbox.rglob("*.phase2-staging-*")), [])

    def assert_attempt_mutation_rejected(
        self,
        attempt_id: str,
        mutate: object,
        error_pattern: str,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-mutated-attempt-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            attempt = clone / "formal" / attempt_id
            mutate(attempt)
            reseal_attempt(clone, attempt_id)
            with self.assertRaisesRegex(ValueError, error_pattern):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_output_equal_to_artifact_root_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-overlap-equal-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            clone = sandbox / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            self.assert_overlap_rejected_without_mutation(sandbox, clone, clone)

    def test_output_parent_of_artifact_root_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-overlap-parent-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            clone = sandbox / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            self.assert_overlap_rejected_without_mutation(sandbox, clone, sandbox)

    def test_output_child_of_artifact_root_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-overlap-child-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            clone = sandbox / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            self.assert_overlap_rejected_without_mutation(sandbox, clone, clone / "generated")

    def test_resolved_output_alias_overlap_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-overlap-alias-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            clone = sandbox / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            alias = sandbox / "artifact-alias"
            alias.symlink_to(clone, target_is_directory=True)
            self.assert_overlap_rejected_without_mutation(sandbox, clone, alias)

    def test_duplicate_authority_mode_omitting_candidate_is_rejected(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][1] = dict(summary["mode_results"][0])
            replace_json(summary_path, summary)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "mode.*tuple|mode.*plan|namespace",
        )

    def test_mode_result_tuple_order_is_exact(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][0], summary["mode_results"][1] = (
                summary["mode_results"][1],
                summary["mode_results"][0],
            )
            replace_json(summary_path, summary)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "mode.*tuple|mode.*plan|order",
        )

    def test_mode_oom_cannot_be_undercounted_by_attempt_summary(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][0]["oom_count"] = 1
            replace_json(summary_path, summary)
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["counters"]["oom"] = 1
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "OOM|oom|counter",
        )

    def test_reported_timeout_cannot_be_undercounted_by_attempt_summary(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][0]["reported_timeout_count"] = 1
            replace_json(summary_path, summary)
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["counters"]["timeout"] = 1
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "timeout|counter",
        )

    def test_authority_fallback_cannot_be_undercounted_by_attempt_summary(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][0]["fallback_count"] = 1
            replace_json(summary_path, summary)
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["counters"]["fallback"] = 1
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "fallback|counter|state",
        )

    def test_per_mode_fallback_count_greater_than_one_is_rejected(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][0]["fallback_count"] = 2
            replace_json(summary_path, summary)
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["counters"]["fallback"] = 2
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq10_ht02__repeat00",
            mutate,
            "fallback.*0 or 1|fallback.*range|fallback.*state",
        )

    def test_report_resolved_execution_must_match_mode(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "candidate/report.json"
            report = json.loads(report_path.read_text())
            report["resolved_execution"] = "cpu-authority"
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "resolved execution|resolved_execution|mode binding",
        )

    def test_report_resolved_contract_must_match_mode_plan(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "candidate/report.json"
            report = json.loads(report_path.read_text())
            report["resolved_contract"] = "full-output"
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "resolved contract|resolved_contract|contract binding",
        )

    def test_mode_status_and_published_source_must_be_coherent(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][0]["published_source"] = "candidate"
            replace_json(summary_path, summary)
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_source"] = "candidate"
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "status|source|state",
        )

    def test_attempt_verified_result_status_must_match_verified_report(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["verified_result_status"] = "candidate_clean"
            replace_json(summary_path, summary)

        self.assert_attempt_mutation_rejected(
            "hq10_ht02__repeat00",
            mutate,
            "verified.*status|status.*summary",
        )

    def test_attempt_verified_consistency_fields_bind_to_comparator(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["verified_fallback_consistent"] = False
            summary["direct_vs_verified_declared_contract_consistent"] = False
            summary["verified_nested_declared_contract_clean"] = False
            replace_json(summary_path, summary)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "verified.*consisten|verified.*contract|comparator.*summary",
        )

    def test_verified_fallback_status_must_match_comparator_outcome(self) -> None:
        def mutate(attempt: Path) -> None:
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][2]["result_status"] = "cpu_fallback_after_comparator_failure"
            summary["verified_result_status"] = "cpu_fallback_after_comparator_failure"
            replace_json(summary_path, summary)
            report_path = attempt / "verified/report.json"
            report = json.loads(report_path.read_text())
            report["result_status"] = "cpu_fallback_after_comparator_failure"
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq10_ht02__repeat00",
            mutate,
            "fallback status|comparator.*status|result status.*comparator",
        )

    def test_candidate_failure_fallback_requires_not_run_comparator(self) -> None:
        def mutate(attempt: Path) -> None:
            status = "cpu_fallback_after_candidate_failure"
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][2]["result_status"] = status
            summary["verified_result_status"] = status
            replace_json(summary_path, summary)
            report_path = attempt / "verified/report.json"
            report = json.loads(report_path.read_text())
            report["result_status"] = status
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq12_ht02__repeat00",
            mutate,
            "candidate failure.*not_run|fallback status.*comparator status",
        )

    def test_decision_narrative_derives_candidate_failure_reason(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-candidate-failure-narrative-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            attempt_id = "hq12_ht02__repeat00"
            attempt = clone / "formal" / attempt_id
            status = "cpu_fallback_after_candidate_failure"
            summary_path = attempt / "attempt-summary.json"
            summary = json.loads(summary_path.read_text())
            summary["mode_results"][2]["result_status"] = status
            summary["verified_result_status"] = status
            replace_json(summary_path, summary)

            comparison = json.loads((attempt / "comparison.json").read_text())
            report_path = attempt / "verified/report.json"
            report = json.loads(report_path.read_text())
            report["result_status"] = status
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
                "metrics": comparison["metrics"],
            }
            replace_json(report_path, report)
            reseal_attempt(clone, attempt_id)

            output = Path(temp_name) / "output"
            self.module.generate(ROOT, output, artifact_root=clone)
            decision = (output / "phase2_decision.md").read_text(encoding="utf-8")
            self.assertIn("the two declared-contract mismatches", decision)
            self.assertIn("one candidate failure (`hq12_ht02`)", decision)
            self.assertNotIn("comparator-detail failure (`hq12_ht02`)", decision)

    def test_report_input_paths_must_bind_to_snapshot_inputs(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["inputs"]["query"]["path"] = report["inputs"]["target"]["path"]
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "query.*path|snapshot.*input|input.*binding",
        )

    def test_report_backend_paths_must_bind_to_snapshot_binaries(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["authority_backend"] = report["candidate_backend"]
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "authority.*path|snapshot.*binary|backend.*binding",
        )

    def test_unreported_published_output_file_is_rejected(self) -> None:
        def mutate(attempt: Path) -> None:
            (attempt / "authority/output/unreported.txt").write_text("not in report\n", encoding="utf-8")

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "published output.*set|unreported|output tree",
        )

    def test_reported_published_output_missing_from_tree_is_rejected(self) -> None:
        def mutate(attempt: Path) -> None:
            (attempt / "authority/output/wrapper-stderr.log").unlink()

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "published output.*missing|published output.*set|output tree",
        )

    def test_published_output_report_row_cannot_be_omitted(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"] = report["published_outputs"][:-1]
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "published output.*set|published output.*manifest|output tree",
        )

    def test_published_output_size_must_match_file(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"][0]["size_bytes"] += 1
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "published output.*size|size.*drift",
        )

    def test_published_output_sha256_must_match_file(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"][0]["sha256"] = "0" * 64
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "published output.*checksum|published output.*sha|checksum.*drift",
        )

    def test_published_output_record_count_has_tsv_semantics(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"][0]["record_count"] += 1
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "record count|record_count|published output.*record",
        )

    def test_escaping_published_output_relative_path_is_rejected(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"][0]["relative_path"] = "../outside"
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "unsafe.*published output|relative.*path",
        )

    def test_duplicate_published_output_relative_path_is_rejected(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"].append(dict(report["published_outputs"][0]))
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "duplicate.*published output|published output.*duplicate",
        )

    def test_published_output_absolute_path_must_match_namespace(self) -> None:
        def mutate(attempt: Path) -> None:
            report_path = attempt / "authority/report.json"
            report = json.loads(report_path.read_text())
            report["published_outputs"][0]["path"] = report["published_outputs"][0]["path"].replace(
                "/authority/output/", "/candidate/output/"
            )
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "published output.*path|path.*namespace",
        )

    def test_verified_candidate_clean_publication_has_exact_two_file_shape(self) -> None:
        def mutate(attempt: Path) -> None:
            extra = attempt / "verified/output/extra.txt"
            extra.write_text("unexpected candidate-clean output\n", encoding="utf-8")
            report_path = attempt / "verified/report.json"
            report = json.loads(report_path.read_text())
            output_prefix = Path(report["published_outputs"][0]["path"]).parent
            report["published_outputs"].append({
                "path": str(output_prefix / extra.name),
                "relative_path": extra.name,
                "size_bytes": extra.stat().st_size,
                "sha256": hashlib.sha256(extra.read_bytes()).hexdigest(),
                "record_count": None,
            })
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq01_ht01__repeat00",
            mutate,
            "candidate-clean.*shape|verified.*shape",
        )

    def test_verified_fallback_publication_has_authority_relative_tree(self) -> None:
        def mutate(attempt: Path) -> None:
            output = attempt / "verified/output"
            original = next(output.glob("*-TFOsorted"))
            renamed = output / f"renamed-{original.name}"
            original.rename(renamed)
            report_path = attempt / "verified/report.json"
            report = json.loads(report_path.read_text())
            row = next(item for item in report["published_outputs"] if item["relative_path"] == original.name)
            row["relative_path"] = renamed.name
            row["path"] = str(Path(row["path"]).with_name(renamed.name))
            replace_json(report_path, report)

        self.assert_attempt_mutation_rejected(
            "hq10_ht02__repeat00",
            mutate,
            "fallback.*tree.*authority|authority-shaped",
        )

    def assert_symlinked_artifact_directory_rejected(self, relative: str) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-symlink-tree-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            clone = sandbox / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            source = clone / relative
            external = sandbox / "external-target"
            source.rename(external)
            source.symlink_to(external, target_is_directory=True)
            before = fingerprint_tree_no_follow(external)
            with self.assertRaisesRegex(ValueError, "symlink|real directory|no-follow"):
                self.module.generate(ROOT, sandbox / "output", artifact_root=clone)
            self.assertEqual(fingerprint_tree_no_follow(external), before)

    def test_symlinked_formal_root_is_rejected_without_following_target(self) -> None:
        self.assert_symlinked_artifact_directory_rejected("formal")

    def test_symlinked_pilot_root_is_rejected_without_following_target(self) -> None:
        self.assert_symlinked_artifact_directory_rejected("pilot")

    def test_symlinked_attempt_internal_parent_is_rejected_without_following_target(self) -> None:
        self.assert_symlinked_artifact_directory_rejected(
            "formal/hq01_ht01__repeat00/execution-snapshot/inputs"
        )

    def test_checker_snapshot_rejects_symlink_without_following_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-checker-symlink-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            fixture = sandbox / "frozen"
            fixture.mkdir()
            external = sandbox / "external.txt"
            external.write_text("external sentinel\n", encoding="utf-8")
            (fixture / "linked.txt").symlink_to(external)
            before = fingerprint_tree_no_follow(external)
            completed = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts/check_bioinformatics_phase2.sh"),
                    "--snapshot-frozen-tree",
                    str(fixture),
                    str(sandbox / "snapshot.json"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertRegex(completed.stdout + completed.stderr, "symlink|unexpected frozen tree entry")
            self.assertEqual(fingerprint_tree_no_follow(external), before)

    def test_missing_attempt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-missing-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            shutil.rmtree(clone / "formal/hq12_ht02__repeat00")
            with self.assertRaisesRegex(ValueError, "missing.*attempt|attempt set drift"):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_extra_attempt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-extra-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            (clone / "formal/unplanned__repeat00").mkdir()
            with self.assertRaisesRegex(ValueError, "extra.*attempt|attempt set drift"):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_extra_root_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-extra-artifact-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            (clone / "unrecorded-result.txt").write_text("not in the formal ledger\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact root set drift|extra artifact"):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_tampered_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-tamper-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            path = clone / "formal/hq01_ht01__repeat00/attempt-summary.json"
            replace_copy(path, path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "checksum|size drift|not canonical"):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_unfavorable_formal_row_deletion_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-row-delete-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            table = clone / "formal-attempts.tsv"
            lines = table.read_text(encoding="utf-8").splitlines()
            filtered = [line for line in lines if not line.startswith("hq10_ht02__repeat00\t")]
            replace_copy(table, ("\n".join(filtered) + "\n").encode("utf-8"))
            with self.assertRaisesRegex(ValueError, "formal-attempts|representation|attempt set drift"):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_wrong_execution_epoch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-epoch-", dir=ROOT / ".tmp") as temp_name:
            clone = Path(temp_name) / "frozen"
            hardlink_copytree(FROZEN_ROOT, clone)
            path = clone / "formal/hq01_ht01__repeat00/attempt-config.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["git_head"] = "0" * 40
            replace_copy(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            with self.assertRaisesRegex(ValueError, "checksum|checkpoint|git_head|config digest"):
                self.module.generate(ROOT, Path(temp_name) / "output", artifact_root=clone)

    def test_transactional_publication_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-rollback-") as temp_name:
            output = Path(temp_name) / "paper"
            output.mkdir()
            originals = {name: f"old:{name}\n" for name in OUTPUT_NAMES}
            for name, payload in originals.items():
                (output / name).write_text(payload, encoding="utf-8")

            def fail_after_third(step: int, _name: str) -> None:
                if step == 3:
                    raise RuntimeError("injected publication failure")

            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.module.publish_outputs_transactionally(
                    output,
                    {name: f"new:{name}\n" for name in OUTPUT_NAMES},
                    after_replace=fail_after_third,
                )
            self.assertEqual(
                {name: (output / name).read_text(encoding="utf-8") for name in OUTPUT_NAMES},
                originals,
            )

    def test_transactional_publication_fsyncs_existing_file_backups(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-backup-fsync-", dir=ROOT / ".tmp") as temp_name:
            output = Path(temp_name) / "paper"
            output.mkdir()
            for name in OUTPUT_NAMES:
                (output / name).write_text(f"old:{name}\n", encoding="utf-8")
            fsynced_names: list[str] = []
            real_fsync = self.module.os.fsync

            def recording_fsync(descriptor: int) -> None:
                fsynced_names.append(Path(os.readlink(f"/proc/self/fd/{descriptor}")).name)
                real_fsync(descriptor)

            self.module.os.fsync = recording_fsync
            try:
                self.module.publish_outputs_transactionally(
                    output,
                    {name: f"new:{name}\n" for name in OUTPUT_NAMES},
                )
            finally:
                self.module.os.fsync = real_fsync
            self.assertTrue(
                {f"{name}.backup" for name in OUTPUT_NAMES}.issubset(fsynced_names),
                fsynced_names,
            )

    def assert_publication_symlink_rejected_without_mutation(
        self,
        sandbox: Path,
        output: Path,
    ) -> None:
        before = fingerprint_tree_no_follow(sandbox)
        error: ValueError | None = None
        try:
            self.module.publish_outputs_transactionally(
                output,
                {name: f"new:{name}\n" for name in OUTPUT_NAMES},
            )
        except ValueError as exc:
            error = exc
        self.assertEqual(fingerprint_tree_no_follow(sandbox), before)
        self.assertIsNotNone(error, "symlinked publication destination was accepted")
        self.assertRegex(str(error), "symlink|real directory|regular file")
        self.assertEqual(list(sandbox.rglob("*.phase2-staging-*")), [])

    def test_symlinked_publication_output_directory_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-publish-dir-link-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            external = sandbox / "external"
            external.mkdir()
            output = sandbox / "paper"
            output.symlink_to(external, target_is_directory=True)
            self.assert_publication_symlink_rejected_without_mutation(sandbox, output)

    def test_symlinked_publication_parent_component_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-publish-parent-link-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            external = sandbox / "external"
            external.mkdir()
            alias = sandbox / "alias"
            alias.symlink_to(external, target_is_directory=True)
            self.assert_publication_symlink_rejected_without_mutation(sandbox, alias / "paper")

    def test_symlinked_publication_destination_file_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase2-publish-file-link-", dir=ROOT / ".tmp") as temp_name:
            sandbox = Path(temp_name)
            output = sandbox / "paper"
            output.mkdir()
            external = sandbox / "external.txt"
            external.write_text("external sentinel\n", encoding="utf-8")
            (output / OUTPUT_NAMES[0]).symlink_to(external)
            self.assert_publication_symlink_rejected_without_mutation(sandbox, output)


if __name__ == "__main__":
    unittest.main()
