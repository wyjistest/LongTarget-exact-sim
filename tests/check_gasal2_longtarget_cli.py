#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/gasal2_longtarget.py"
SCHEMA = ROOT / "schemas/gasal2_longtarget_run_report.schema.json"
ORACLE = ROOT / "tests/oracle/hg19-H19-testDNA-TFOsorted"
sys.path.insert(0, str(ROOT / "scripts"))
from gasal2_longtarget import (  # noqa: E402
    TFOSORTED_COLUMNS,
    WorkflowError,
    validate_report,
    validate_schema_value,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Gasal2LongTargetCliTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="gasal2-longtarget-cli-")
        self.work = Path(self.temp.name)
        self.query = self.work / "query.fa"
        self.target = self.work / "target.fa"
        self.query.write_text(">query\nACGTACGTACGT\n", encoding="utf-8")
        self.target.write_text(">target\n" + "ACGT" * 50 + "\n", encoding="utf-8")
        self.authority = self.make_backend("authority", "clean")
        self.candidate = self.make_backend("candidate", "clean")
        self.output = self.work / "result"
        self.report = self.work / "run-report.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_backend(self, name: str, behavior: str) -> Path:
        path = self.work / f"{name}.py"
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import os
                import sys
                import time
                from pathlib import Path

                behavior = {behavior!r}
                for option in ('-f1', '-f2'):
                    input_path = Path(sys.argv[sys.argv.index(option) + 1])
                    if not input_path.is_file():
                        print(f'missing backend input: {{input_path}}', file=sys.stderr)
                        raise SystemExit(11)
                output = Path(sys.argv[sys.argv.index('-O') + 1])
                if not output.is_dir():
                    print(f'missing backend output directory: {{output}}', file=sys.stderr)
                    raise SystemExit(12)
                marker = os.environ.get('FAKE_{name.upper()}_STARTED_MARKER') or os.environ.get('FAKE_STARTED_MARKER')
                if marker:
                    Path(marker).write_text('started\\n', encoding='utf-8')
                if behavior == 'slow':
                    time.sleep(60)
                if behavior in {{'failure', 'oom'}}:
                    (output / 'partial.txt').write_text('partial\\n', encoding='utf-8')
                    print('CUDA out of memory' if behavior == 'oom' else 'backend failure', file=sys.stderr)
                    raise SystemExit(9)
                source = Path(os.environ['FAKE_ORACLE'])
                destination = output / 'fixture-TFOsorted'
                if behavior == 'empty':
                    (output / 'backend.txt').write_text({name!r} + '\\n', encoding='utf-8')
                    raise SystemExit(0)
                if behavior == 'malformed':
                    destination.write_text('not-a-tfosorted-header\\n', encoding='utf-8')
                    (output / 'backend.txt').write_text({name!r} + '\\n', encoding='utf-8')
                    raise SystemExit(0)
                source_lines = source.read_text(encoding='utf-8').splitlines()
                current_lines = []
                for line_number, line in enumerate(source_lines):
                    columns = line.split('\\t')
                    if line_number == 0:
                        columns.insert(5, 'Chr')
                        columns.append('TTS sequence')
                    else:
                        columns.insert(5, 'chrTest')
                        columns.append('ACGT')
                    current_lines.append('\\t'.join(columns))
                if behavior == 'stability_mismatch':
                    header = current_lines[0].split('\\t')
                    score_index = header.index('Score')
                    stability_index = header.index('MeanStability')
                    rows = [line.split('\\t') for line in current_lines[1:]]
                    selected = min(rows, key=lambda row: float(row[score_index]))
                    selected[stability_index] = '999999'
                    current_lines = [current_lines[0], *('\\t'.join(row) for row in rows)]
                if behavior == 'invalid_numeric':
                    header = current_lines[0].split('\\t')
                    score_index = header.index('Score')
                    first_row = current_lines[1].split('\\t')
                    first_row[score_index] = 'not-a-number'
                    current_lines[1] = '\\t'.join(first_row)
                if behavior == 'mismatch':
                    destination.write_text(current_lines[0] + '\\n', encoding='utf-8')
                else:
                    destination.write_text('\\n'.join(current_lines) + '\\n', encoding='utf-8')
                (output / 'backend.txt').write_text({name!r} + '\\n', encoding='utf-8')
                print('fake_backend={name}')
                """
            ),
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def make_comparator(
        self,
        name: str,
        *,
        returncode: int,
        sleep_seconds: int = 0,
        full_missing_rows: str = "0",
        details_rank: str | None = None,
        details_sides: tuple[str, ...] = ("candidate",),
    ) -> Path:
        path = self.work / f"{name}.py"
        details_payload = None
        if details_rank is not None:
            header = ["side", "kind", "mode", "rank", "cluster_id", *TFOSORTED_COLUMNS]
            rows = [
                [side, "clustered", "score", details_rank, "cluster-1", *(["value"] * 19)]
                for side in details_sides
            ]
            details_payload = (header, rows)
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import sys
                import time
                from pathlib import Path

                details_payload = {details_payload!r}
                if details_payload is not None:
                    details_header, details_rows = details_payload
                    details = Path(sys.argv[sys.argv.index('--details') + 1])
                    details.write_text(
                        '\\t'.join(details_header) + '\\n' +
                        ''.join('\\t'.join(row) + '\\n' for row in details_rows),
                        encoding='utf-8',
                    )

                for line in (
                    'full_missing_rows={full_missing_rows}',
                    'full_extra_rows=0',
                    'clustered_score_top5_equal=1',
                    'clustered_stability_top5_equal=1',
                    'clustered_nt_top5_equal=1',
                    'boundary_ties_equal=1',
                ):
                    print(line, flush=True)
                time.sleep({sleep_seconds})
                raise SystemExit({returncode})
                """
            ),
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def environment(self, *, gpus: bool = True) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "FAKE_ORACLE": str(ORACLE),
                "GASAL2_LONGTARGET_TEST_MODE": "1",
                "GASAL2_LONGTARGET_TEST_GPU_JSON": json.dumps(
                    [
                        {
                            "index": 0,
                            "name": "Test GPU",
                            "memory_total_mib": 24564,
                            "driver_version": "test",
                            "compute_capability": "8.9",
                        }
                    ]
                    if gpus
                    else []
                ),
            }
        )
        return env

    def command(self, *extra: str, output: Path | None = None, report: Path | None = None) -> list[str]:
        return [
            sys.executable,
            str(CLI),
            "--query",
            str(self.query),
            "--target",
            str(self.target),
            "--output",
            str(output or self.output),
            "--report",
            str(report or self.report),
            "--authority-binary",
            str(self.authority),
            "--candidate-binary",
            str(self.candidate),
            *extra,
        ]

    def run_cli(
        self,
        *extra: str,
        env: dict[str, str] | None = None,
        output: Path | None = None,
        report: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.command(*extra, output=output, report=report),
            cwd=ROOT,
            env=env or self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )

    def load_report(self, path: Path | None = None) -> dict[str, object]:
        report = json.loads((path or self.report).read_text(encoding="utf-8"))
        validate_report(report)
        return report

    def assert_published_by(self, backend: str, output: Path | None = None) -> None:
        self.assertEqual(self.load_report()["published_source"], backend)
        if backend == "authority":
            self.assertEqual((output or self.output).joinpath("backend.txt").read_text().strip(), backend)

    def test_cpu_authority_small_fixture_publishes_report_and_output(self) -> None:
        result = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["mode"], "cpu-authority")
        self.assertEqual(report["result_status"], "authority_complete")
        self.assertEqual(report["requested_contract"], "auto")
        self.assertEqual(report["resolved_contract"], "all-ranked-top5")
        self.assertEqual(report["inputs"]["query"]["sha256"], sha256(self.query))
        self.assertTrue(report["published_outputs"])

    def test_default_safe_uses_verified_before_contract_promotion(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("candidate")
        report = self.load_report()
        self.assertEqual(report["mode"], "safe")
        self.assertEqual(report["resolved_execution"], "verified")
        self.assertEqual(report["result_status"], "candidate_clean")
        self.assertTrue(report["comparators"]["all_ranked_top5_equal"])

    def test_safe_without_gpu_falls_back_before_candidate_execution(self) -> None:
        candidate_marker = self.work / "candidate-started"
        env = self.environment(gpus=False)
        env["FAKE_CANDIDATE_STARTED_MARKER"] = str(candidate_marker)
        result = self.run_cli(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        self.assertFalse(candidate_marker.exists())
        report = self.load_report()
        self.assertEqual(report["resolved_execution"], "cpu-authority")
        self.assertEqual(report["result_status"], "authority_complete")
        self.assertIn("candidate environment is not eligible", " ".join(report["warnings"]))

    def test_verified_clean_fixture_publishes_candidate(self) -> None:
        result = self.run_cli("--mode", "verified", "--contract", "all-ranked-top5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("candidate")
        report = self.load_report()
        self.assertEqual(report["result_status"], "candidate_clean")
        self.assertEqual(report["comparators"]["score_top5_equal"], True)
        self.assertEqual(report["comparators"]["stability_top5_equal"], True)
        self.assertEqual(report["comparators"]["nt_top5_equal"], True)
        self.assertFalse(any(path.name.endswith("-TFOsorted") for path in self.output.iterdir()))
        contract_output = self.output / "gasal2-longtarget-all-ranked-top5.tsv"
        self.assertTrue(contract_output.is_file())
        self.assertEqual(len(contract_output.read_text(encoding="utf-8").splitlines()), 16)
        contract_receipt = next(
            row
            for row in report["published_outputs"]
            if row["relative_path"] == contract_output.name
        )
        self.assertEqual(contract_receipt["record_count"], 15)

    def test_score_contract_publishes_only_score_ranked_candidate_rows(self) -> None:
        self.candidate = self.make_backend("candidate", "stability_mismatch")
        result = self.run_cli("--mode", "verified", "--contract", "score-top5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("candidate")
        report = self.load_report()
        self.assertTrue(report["comparators"]["score_top5_equal"])
        self.assertFalse(report["comparators"]["stability_top5_equal"])
        self.assertTrue(report["comparators"]["declared_contract_clean"])
        contract_output = self.output / "gasal2-longtarget-score-top5.tsv"
        lines = contract_output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 6)
        self.assertTrue(all(line.startswith("score\t") for line in lines[1:]))
        self.assertFalse(any(path.name.endswith("-TFOsorted") for path in self.output.iterdir()))

    def test_verified_mismatch_atomically_publishes_authority(self) -> None:
        self.candidate = self.make_backend("candidate", "mismatch")
        result = self.run_cli("--mode", "verified", "--contract", "all-ranked-top5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        self.assertFalse(any(path.name.startswith(".") for path in self.work.iterdir() if "partial" in path.name))
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_mismatch")
        self.assertFalse(report["comparators"]["all_ranked_top5_equal"])
        self.assertEqual(report["published_source"], "authority")

    def test_candidate_oom_publishes_authority_and_records_failure(self) -> None:
        self.candidate = self.make_backend("candidate", "oom")
        result = self.run_cli("--mode", "verified")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_candidate_failure")
        self.assertEqual(report["backends"]["candidate"]["returncode"], 9)
        self.assertEqual(report["counters"]["oom"], 1)
        self.assertEqual(report["counters"]["fallback"], 1)

    def test_fast_experimental_requires_explicit_mode_and_warns(self) -> None:
        result = self.run_cli("--mode", "fast-experimental")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EXPERIMENTAL", result.stderr)
        self.assert_published_by("candidate")
        report = self.load_report()
        self.assertEqual(report["result_status"], "experimental_unverified")
        self.assertEqual(report["resolved_contract"], "experimental-native")
        self.assertEqual(report["comparators"]["status"], "not_run")
        self.assertNotIn("safe", report["result_status"])
        contract = json.loads((self.output / "contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contract_id"], "experimental-native")
        self.assertEqual(contract["status"], "experimental_unverified")
        self.assertTrue(contract["raw_candidate_output_published"])

    def test_fast_experimental_rejects_named_product_contract(self) -> None:
        result = self.run_cli("--mode", "fast-experimental", "--contract", "score-top5")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.output.exists())
        report = self.load_report()
        self.assertEqual(report["result_status"], "unsupported_contract")

    def test_query_length_guard_fails_before_backend(self) -> None:
        self.query.write_text(">too_long\n" + "A" * 2813 + "\n", encoding="utf-8")
        marker = self.work / "started"
        env = self.environment()
        env["FAKE_STARTED_MARKER"] = str(marker)
        result = self.run_cli("--mode", "fast-experimental", env=env)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())
        self.assertFalse(marker.exists())
        report = self.load_report()
        self.assertEqual(report["result_status"], "invalid_input")
        self.assertIn("2812", " ".join(report["errors"]))

    def test_malformed_fasta_and_unsupported_contract_fail_closed(self) -> None:
        self.query.write_text("ACGT without header\n", encoding="utf-8")
        malformed = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(malformed.returncode, 2)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "invalid_input")

        self.query.write_text(">query\nACGT\n", encoding="utf-8")
        self.report.unlink()
        unsupported = self.run_cli("--mode", "fast-experimental", "--contract", "full-output")
        self.assertEqual(unsupported.returncode, 2)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "unsupported_contract")

    def test_multiple_query_records_are_rejected_before_authority_execution(self) -> None:
        self.query.write_text(">query1\nACGT\n>query2\nTGCA\n", encoding="utf-8")
        marker = self.work / "authority-started"
        env = self.environment(gpus=False)
        env["FAKE_AUTHORITY_STARTED_MARKER"] = str(marker)
        result = self.run_cli(env=env)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse(self.output.exists())
        report = self.load_report()
        self.assertEqual(report["result_status"], "invalid_input")
        self.assertIn("exactly one query", " ".join(report["errors"]))

    def test_output_collision_fails_without_overwrite(self) -> None:
        self.output.mkdir()
        (self.output / "owner-data.txt").write_text("keep\n", encoding="utf-8")
        result = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.output / "owner-data.txt").read_text(), "keep\n")
        self.assertEqual(self.load_report()["result_status"], "invalid_input")

    def test_dry_run_writes_preflight_report_without_executing(self) -> None:
        marker = self.work / "started"
        env = self.environment()
        env["FAKE_STARTED_MARKER"] = str(marker)
        result = self.run_cli("--dry-run", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse(self.output.exists())
        report = self.load_report()
        self.assertEqual(report["result_status"], "dry_run")
        self.assertTrue(report["preflight"]["passed"])
        self.assertTrue(report["planned_commands"])

    def test_report_matches_schema_required_fields(self) -> None:
        result = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(result.returncode, 0, result.stderr)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = self.load_report()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        validate_report(report)

    def test_schema_rejects_missing_or_mistyped_nested_fields(self) -> None:
        result = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(result.returncode, 0, result.stderr)
        original = self.load_report()
        mutations = {
            "query_length_max": lambda report: report["inputs"]["query"].pop("length_max"),
            "target_total_bp": lambda report: report["inputs"]["target"].pop("total_bp"),
            "environment_cpu_model": lambda report: report["environment"].pop("cpu_model"),
            "authority_wall_seconds": lambda report: report["backends"]["authority"].pop("wall_seconds"),
            "comparator_boundary_ties": lambda report: report["comparators"].pop("boundary_ties_equal"),
            "query_lengths_type": lambda report: report["inputs"]["query"].update(lengths="invalid"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                report = json.loads(json.dumps(original))
                mutate(report)
                with self.assertRaises(WorkflowError):
                    validate_report(report)

    def test_shared_schema_validator_enforces_supported_safety_keywords(self) -> None:
        schema = {
            "type": "object",
            "required": ["name", "values", "count"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "values": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
                "count": {"type": "integer", "minimum": 1, "maximum": 3},
            },
        }
        validate_schema_value(schema, {"name": "safe", "values": ["8.9"], "count": 2}, "fixture")
        invalid_values = [
            {"name": "safe", "values": ["8.9"], "count": 2, "extra": True},
            {"name": "", "values": ["8.9"], "count": 2},
            {"name": "safe", "values": [], "count": 2},
            {"name": "safe", "values": ["8.9", "8.9"], "count": 2},
            {"name": "safe", "values": ["8.9"], "count": 0},
            {"name": "safe", "values": ["8.9"], "count": 4},
        ]
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_schema_value(schema, value, "fixture")

    def test_comparator_abnormal_exit_with_clean_metrics_publishes_authority(self) -> None:
        comparator = self.make_comparator("abnormal-comparator", returncode=9)
        result = self.run_cli("--mode", "verified", "--comparator", str(comparator))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["status"], "failed")
        self.assertEqual(report["comparators"]["returncode"], 9)

    def test_comparator_timeout_with_clean_metrics_publishes_authority(self) -> None:
        comparator = self.make_comparator("slow-comparator", returncode=0, sleep_seconds=10)
        result = self.run_cli(
            "--mode",
            "verified",
            "--comparator",
            str(comparator),
            "--timeout",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["returncode"], 124)
        self.assertEqual(report["counters"]["timeout"], 1)

    def test_comparator_without_details_publishes_authority(self) -> None:
        comparator = self.make_comparator("no-details-comparator", returncode=0)
        result = self.run_cli("--mode", "verified", "--comparator", str(comparator))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["status"], "failed")
        self.assertIn("details", report["comparators"]["failure_reason"])

    def test_comparator_with_invalid_metrics_publishes_authority(self) -> None:
        comparator = self.make_comparator(
            "invalid-metrics-comparator",
            returncode=0,
            full_missing_rows="not-an-integer",
        )
        result = self.run_cli("--mode", "verified", "--comparator", str(comparator))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["status"], "failed")
        self.assertIn("metric", report["comparators"]["failure_reason"])

    def test_comparator_with_invalid_details_rank_publishes_authority(self) -> None:
        comparator = self.make_comparator(
            "invalid-details-comparator",
            returncode=0,
            details_rank="not-an-integer",
        )
        result = self.run_cli("--mode", "verified", "--comparator", str(comparator))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["status"], "failed")
        self.assertIn("details", report["comparators"]["failure_reason"])

    def test_comparator_with_incomplete_details_publishes_authority(self) -> None:
        comparator = self.make_comparator(
            "incomplete-details-comparator",
            returncode=0,
            details_rank="1",
        )
        result = self.run_cli(
            "--mode",
            "verified",
            "--contract",
            "score-top5",
            "--comparator",
            str(comparator),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["status"], "failed")
        self.assertIn("details", report["comparators"]["failure_reason"])

    def test_comparator_with_fabricated_symmetric_details_publishes_authority(self) -> None:
        comparator = self.make_comparator(
            "fabricated-details-comparator",
            returncode=0,
            details_rank="1",
            details_sides=("baseline", "candidate"),
        )
        result = self.run_cli(
            "--mode",
            "verified",
            "--contract",
            "score-top5",
            "--comparator",
            str(comparator),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_published_by("authority")
        report = self.load_report()
        self.assertEqual(report["result_status"], "cpu_fallback_after_comparator_failure")
        self.assertEqual(report["comparators"]["status"], "failed")
        self.assertIn("details", report["comparators"]["failure_reason"])

    def test_successful_backend_must_emit_valid_tfosorted(self) -> None:
        self.authority = self.make_backend("authority", "empty")
        empty = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(empty.returncode, 4, empty.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "authority_failure")

        self.authority = self.make_backend("authority", "clean")
        self.candidate = self.make_backend("candidate", "malformed")
        self.report.unlink()
        malformed = self.run_cli("--mode", "fast-experimental")
        self.assertEqual(malformed.returncode, 5, malformed.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "candidate_failure")

    def test_backend_with_invalid_numeric_tfosorted_fails_closed(self) -> None:
        self.authority = self.make_backend("authority", "invalid_numeric")
        authority = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(authority.returncode, 4, authority.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "authority_failure")

        self.authority = self.make_backend("authority", "clean")
        self.candidate = self.make_backend("candidate", "invalid_numeric")
        self.report.unlink()
        candidate = self.run_cli("--mode", "fast-experimental")
        self.assertEqual(candidate.returncode, 5, candidate.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "candidate_failure")

    def test_paths_with_spaces_and_shell_metacharacters_are_not_executed(self) -> None:
        dangerous = self.work / "space $(touch injected)"
        dangerous.mkdir()
        query = dangerous / "query file.fa"
        target = dangerous / "target ; file.fa"
        query.write_text(">query\nACGT\n", encoding="utf-8")
        target.write_text(">target\nACGTACGT\n", encoding="utf-8")
        self.query = query
        self.target = target
        output = dangerous / "output dir"
        report = dangerous / "report file.json"
        result = self.run_cli("--mode", "cpu-authority", output=output, report=report)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((output / "backend.txt").read_text().strip(), "authority")
        self.assertFalse((ROOT / "injected").exists())
        self.assertEqual(json.loads(report.read_text())["result_status"], "authority_complete")

    def test_relative_paths_are_resolved_before_backend_cwd_change(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--mode",
                "cpu-authority",
                "--query",
                self.query.name,
                "--target",
                self.target.name,
                "--output",
                "relative-output",
                "--report",
                "relative-report.json",
                "--authority-binary",
                str(self.authority),
                "--candidate-binary",
                str(self.candidate),
            ],
            cwd=self.work,
            env=self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.work / "relative-output/backend.txt").read_text().strip(), "authority")

    def test_non_utf8_fasta_is_classified_as_invalid_input(self) -> None:
        self.query.write_bytes(b">query\nACGT\xff\n")
        result = self.run_cli("--mode", "cpu-authority")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.load_report()["result_status"], "invalid_input")
        self.assertFalse(self.output.exists())

    def test_interrupt_never_publishes_partial_output(self) -> None:
        self.authority = self.make_backend("authority", "slow")
        marker = self.work / "started"
        env = self.environment()
        env["FAKE_STARTED_MARKER"] = str(marker)
        process = subprocess.Popen(
            self.command("--mode", "cpu-authority"),
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.time() + 10
        while time.time() < deadline and not marker.exists() and process.poll() is None:
            time.sleep(0.05)
        self.assertTrue(marker.exists(), "fake backend did not start")
        process.send_signal(signal.SIGTERM)
        _, stderr = process.communicate(timeout=10)
        self.assertNotEqual(process.returncode, 0, stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.load_report()["result_status"], "interrupted")
        partials = [path for path in self.work.iterdir() if ".partial." in path.name]
        self.assertEqual(partials, [])

    def test_help_and_version_are_stable(self) -> None:
        help_result = subprocess.run(
            [sys.executable, str(CLI), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for token in ("--mode", "--contract", "--query", "--target", "--output", "--report", "--dry-run"):
            self.assertIn(token, help_result.stdout)
        version_result = subprocess.run(
            [sys.executable, str(CLI), "--version"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(version_result.returncode, 0, version_result.stderr)
        self.assertRegex(version_result.stdout.strip(), r"^gasal2-longtarget [0-9]+\.[0-9]+\.[0-9]+")

    def test_phase1_checker_cleans_only_its_unique_work_child(self) -> None:
        checker = (ROOT / "scripts/check_bioinformatics_phase1.sh").read_text(encoding="utf-8")
        self.assertIn('RUN_WORK="$(mktemp -d "$WORK_ROOT/run.XXXXXX")"', checker)
        self.assertIn('rm -rf -- "$RUN_WORK"', checker)
        self.assertNotIn('rm -rf "$WORK"', checker)
        self.assertIn('print("cli_contract_tests=32")', checker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
