#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "reproduce/bioinformatics/run_holdout.py"
PROTOCOL = ROOT / "paper/bioinformatics/holdout_execution_protocol.md"
MANIFEST = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
EXPECTED_FREEZE_ID = "bioinformatics-phase2-holdout-v1-9e293b2c"
EXPECTED_MANIFEST_SHA256 = "9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_runner():
    if not RUNNER.is_file():
        raise AssertionError(f"missing holdout runner: {RUNNER}")
    spec = importlib.util.spec_from_file_location("bioinformatics_holdout_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load holdout runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_manifest(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def write_manifest(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class HoldoutPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def copy_freeze(self) -> Path:
        destination = self.work / "repo"
        manifest = destination / "paper/bioinformatics/holdout_manifest.tsv"
        manifest.parent.mkdir(parents=True)
        shutil.copy2(MANIFEST, manifest)
        source_inputs = ROOT / "reproduce/bioinformatics/holdout_inputs"
        shutil.copytree(source_inputs, destination / "reproduce/bioinformatics/holdout_inputs")
        return manifest

    @contextmanager
    def semantic_mutation(self, mutate):
        manifest = self.copy_freeze()
        fields, rows = read_manifest(manifest)
        mutate(fields, rows)
        write_manifest(manifest, fields, rows)
        with mock.patch.object(self.runner, "MANIFEST_SHA256", sha256(manifest)):
            yield manifest

    def test_build_plan_has_exact_frozen_expansion(self) -> None:
        plan = self.runner.build_plan(MANIFEST)
        self.assertEqual(plan["freeze_id"], EXPECTED_FREEZE_ID)
        self.assertEqual(plan["manifest_sha256"], EXPECTED_MANIFEST_SHA256)
        self.assertEqual(plan["workload_count"], 24)
        self.assertEqual(plan["formal_attempt_count"], 36)
        self.assertEqual(plan["top_level_run_count"], 108)
        self.assertEqual(plan["backend_execution_count"], 144)
        self.assertEqual(plan["pilot"]["attempt_id"], "pilot__hq01_ht01__repeat00")
        attempts = plan["formal_attempts"]
        self.assertEqual(len(attempts), 36)
        self.assertEqual(len({row["attempt_id"] for row in attempts}), 36)
        self.assertEqual(attempts[0]["attempt_id"], "hq01_ht01__repeat00")
        self.assertEqual(attempts[-1]["attempt_id"], "hq12_ht02__repeat00")
        _, manifest_rows = read_manifest(MANIFEST)
        first_manifest_row = manifest_rows[0]
        for field in (
            "query_file_sha256",
            "query_sequence_sha256",
            "target_file_sha256",
            "target_sequence_sha256",
        ):
            self.assertIn(field, attempts[0])
            self.assertIn(field, plan["pilot"])
            self.assertEqual(attempts[0][field], first_manifest_row[field])
            self.assertEqual(plan["pilot"][field], first_manifest_row[field])
        self.assertEqual(plan["resource_bounds"]["backend_timeout_seconds"], 3600)
        self.assertGreater(plan["resource_bounds"]["max_backend_wall_seconds"], 0)

    def test_plan_only_is_byte_stable_and_creates_no_artifact_root(self) -> None:
        artifact_root = self.work / "must not exist"
        command = [
            sys.executable,
            str(RUNNER),
            "--manifest",
            str(MANIFEST),
            "--artifact-root",
            str(artifact_root),
            "--plan-only",
        ]
        first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        second = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["formal_attempt_count"], 36)
        self.assertFalse(artifact_root.exists())

        canonical = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
        self.assertFalse(canonical.exists())
        default_root = subprocess.run(
            [sys.executable, str(RUNNER), "--manifest", str(MANIFEST), "--plan-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(default_root.returncode, 0, default_root.stderr)
        self.assertFalse(canonical.exists())

    def test_manifest_byte_drift_is_rejected_before_planning(self) -> None:
        manifest = self.copy_freeze()
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "manifest.*SHA-256|digest"):
            self.runner.build_plan(manifest)

    def test_exact_manifest_schema_is_required(self) -> None:
        def mutate(fields, rows):
            fields.append("unexpected")
            for row in rows:
                row["unexpected"] = "value"

        with self.semantic_mutation(mutate) as manifest:
            with self.assertRaisesRegex(ValueError, "schema"):
                self.runner.build_plan(manifest)

    def test_status_repeat_and_cartesian_mutations_are_rejected(self) -> None:
        mutations = (
            ("status", lambda fields, rows: rows[0].__setitem__("status", "run")),
            ("repeat", lambda fields, rows: rows[0].__setitem__("repeat_count", "2")),
            (
                "Cartesian|duplicate|pair",
                lambda fields, rows: rows[1].update(
                    workload_id=rows[0]["workload_id"],
                    query_id=rows[0]["query_id"],
                    target_id=rows[0]["target_id"],
                ),
            ),
        )
        for expected, mutation in mutations:
            with self.subTest(expected=expected):
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                self.work = Path(self.temp.name)
                with self.semantic_mutation(mutation) as manifest:
                    with self.assertRaisesRegex(ValueError, expected):
                        self.runner.build_plan(manifest)

    def test_every_query_and_target_file_and_sequence_digest_is_validated(self) -> None:
        fields, original_rows = read_manifest(MANIFEST)
        digest_fields = (
            "query_file_sha256",
            "query_sequence_sha256",
            "target_file_sha256",
            "target_sequence_sha256",
        )
        for field in digest_fields:
            with self.subTest(field=field):
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                self.work = Path(self.temp.name)

                def mutate(_fields, rows, field=field):
                    rows[0][field] = "0" * 64

                with self.semantic_mutation(mutate) as manifest:
                    with self.assertRaisesRegex(ValueError, "digest|SHA-256"):
                        self.runner.build_plan(manifest)

        self.assertEqual(fields, list(self.runner.MANIFEST_SCHEMA))
        self.assertEqual(len(original_rows), 24)

    def test_actual_input_tampering_fails_closed(self) -> None:
        manifest = self.copy_freeze()
        _, rows = read_manifest(manifest)
        query = manifest.parents[2] / rows[0]["query_path"]
        query.write_bytes(query.read_bytes() + b"A")
        with self.assertRaisesRegex(ValueError, "digest|SHA-256"):
            self.runner.build_plan(manifest)


class HoldoutProtocolTests(unittest.TestCase):
    def test_protocol_freezes_pilot_retry_and_failure_rules(self) -> None:
        self.assertTrue(PROTOCOL.is_file(), f"missing execution protocol: {PROTOCOL}")
        text = PROTOCOL.read_text(encoding="utf-8")
        required = (
            "pilot workload = hq01_ht01",
            "pilot is excluded from formal source data",
            "no automatic or replacement retry",
            "later supplemental retries are additive and cannot replace a primary attempt",
            "formal execution requires a checksum-valid pilot receipt",
            "runtime parameters may not change after pilot or holdout results",
            "all technical failures, mismatches, fallback, OOM and timeout outcomes remain represented",
            "stale primary-attempt partials require manual adjudication",
            "never cleaned, replaced, or automatically rerun",
            "`.paper-artifacts/bioinformatics-phase2-holdout-v1`",
            "pinned runner is the execution authority",
            "does not claim to detect manual executions outside the runner",
            "attempt config binds the runner path, runner SHA-256, and Git HEAD",
            "production pilot/formal execution requires a clean tracked and untracked checkout",
            "ignored canonical artifacts are permitted",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


class HoldoutAttemptExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name) / "repo with spaces;literal"
        (self.work / "paper/bioinformatics").mkdir(parents=True)
        (self.work / "inputs").mkdir()
        (self.work / "fake tools").mkdir()
        self.manifest = self.work / "paper/bioinformatics/fake.tsv"
        self.manifest.write_text("synthetic manifest\n", encoding="utf-8")
        self.query = self.work / "inputs/query ; $(touch SHOULD_NOT_EXIST).fa"
        self.target = self.work / "inputs/target [literal].fa"
        self.query.write_text(">q\nACGTACGT\n", encoding="ascii")
        self.target.write_text(">t\n" + "ACGT" * 8 + "\n", encoding="ascii")
        self.workflow = self.work / "fake tools/fake workflow.py"
        self.comparator = self.work / "fake tools/fake comparator.py"
        self.environment_capture = self.work / "fake tools/fake environment.py"
        self.authority_binary = self.work / "fake tools/fake authority"
        self.candidate_binary = self.work / "fake tools/fake candidate"
        self.authority_binary.write_bytes(b"fake authority binary\n")
        self.candidate_binary.write_bytes(b"fake candidate binary\n")
        self._write_fake_tools()
        self.row = {
            "workload_id": "synthetic_ht01",
            "query_id": "synthetic",
            "target_id": "ht01",
            "query_path": str(self.query.relative_to(self.work)),
            "target_path": str(self.target.relative_to(self.work)),
            "query_file_sha256": sha256(self.query),
            "query_sequence_sha256": hashlib.sha256(b"ACGTACGT").hexdigest(),
            "target_file_sha256": sha256(self.target),
            "target_sequence_sha256": hashlib.sha256(("ACGT" * 8).encode("ascii")).hexdigest(),
            "assembly": "GRCh38",
            "annotation_release": "GENCODE v49",
        }
        self.attempt = {
            "attempt_id": "synthetic_ht01__repeat00",
            "workload_id": "synthetic_ht01",
            "repeat_index": 0,
            "query_id": "synthetic",
            "target_id": "ht01",
            "query_path": self.row["query_path"],
            "target_path": self.row["target_path"],
            "query_file_sha256": self.row["query_file_sha256"],
            "query_sequence_sha256": self.row["query_sequence_sha256"],
            "target_file_sha256": self.row["target_file_sha256"],
            "target_sequence_sha256": self.row["target_sequence_sha256"],
            "rule": 0,
            "top_k": 5,
            "assembly": "GRCh38",
            "annotation_release": "GENCODE v49",
        }
        self.tools = self.runner.ExecutionTools(
            workflow=self.workflow,
            comparator=self.comparator,
            environment_capture=self.environment_capture,
            authority_binary=self.authority_binary,
            candidate_binary=self.candidate_binary,
        )
        self.destination_parent = self.work / "artifacts/pilot"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_fake_tools(self) -> None:
        self.workflow.write_text(
            textwrap.dedent(
                """\
                import argparse, hashlib, json, os, sys, time
                from pathlib import Path

                def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
                def input_report(path):
                    data = Path(path).read_bytes()
                    sequence = ''.join(
                        line.strip() for line in data.decode('ascii').splitlines()
                        if line.strip() and not line.startswith('>')
                    )
                    return {
                        'path': str(Path(path).resolve()), 'sha256': hashlib.sha256(data).hexdigest(),
                        'size_bytes': len(data), 'record_count': 1,
                        'length_min': len(sequence), 'length_max': len(sequence),
                        'lengths': [len(sequence)], 'total_bp': len(sequence),
                    }
                def output_report(path, output):
                    records = None
                    if path.name.endswith('-TFOsorted') or path.suffix == '.tsv':
                        records = max(len(path.read_text(encoding='utf-8', errors='replace').splitlines()) - 1, 0)
                    return {
                        'path': str(path.resolve()),
                        'relative_path': str(path.relative_to(output)),
                        'size_bytes': path.stat().st_size,
                        'sha256': sha(path),
                        'record_count': records,
                    }
                def comparator_report(kind):
                    if kind == 'clean':
                        values = (True, True, True, True, True, True, 0, 0)
                        status, rc = 'clean', 0
                    elif kind == 'mismatch':
                        values = (False, False, False, False, False, False, 1, 1)
                        status, rc = 'mismatch', 1
                    elif kind == 'failed':
                        values = (None, None, None, None, None, None, None, None)
                        status, rc = 'failed', 7
                    else:
                        values = (None, None, None, None, None, None, None, None)
                        status, rc = 'not_run', None
                    score, stability, nt, ties, all_ranked, full, missing, extra = values
                    return {
                        'status': status, 'returncode': rc, 'wall_seconds': 0.01 if rc is not None else None,
                        'score_top5_equal': score, 'stability_top5_equal': stability,
                        'nt_top5_equal': nt, 'boundary_ties_equal': ties,
                        'all_ranked_top5_equal': all_ranked, 'full_rows_equal': full,
                        'full_missing_rows': missing, 'full_extra_rows': extra,
                        'metrics': {
                            'clustered_score_top5_equal': int(score) if score is not None else None,
                            'clustered_stability_top5_equal': int(stability) if stability is not None else None,
                            'clustered_nt_top5_equal': int(nt) if nt is not None else None,
                            'boundary_ties_equal': int(ties) if ties is not None else None,
                        },
                    }

                p = argparse.ArgumentParser()
                p.add_argument('--mode', required=True)
                p.add_argument('--contract', required=True)
                p.add_argument('--query', required=True)
                p.add_argument('--target', required=True)
                p.add_argument('--output', required=True)
                p.add_argument('--report', required=True)
                p.add_argument('--rule', required=True)
                p.add_argument('--triplex-preset', required=True)
                p.add_argument('--top-k', required=True)
                p.add_argument('--assembly', required=True)
                p.add_argument('--annotation-release', required=True)
                p.add_argument('--timeout', required=True)
                p.add_argument('--authority-binary', required=True)
                p.add_argument('--candidate-binary', required=True)
                p.add_argument('--comparator', required=True)
                a = p.parse_args()
                scenario = os.environ.get('FAKE_HOLDOUT_SCENARIO', 'success')
                output = Path(a.output)
                if output.exists():
                    print('workflow output already exists', file=sys.stderr)
                    raise SystemExit(88)
                output.mkdir(parents=True)
                if scenario == 'timeout' and a.mode == 'cpu-authority':
                    print('timeout-start', flush=True)
                    time.sleep(5)
                failed = scenario in {'candidate_failure', 'oom'} and a.mode == 'fast-experimental'
                if not failed:
                    columns = (
                        'QueryStart', 'QueryEnd', 'StartInSeq', 'EndInSeq', 'Direction',
                        'Chr', 'StartInGenome', 'EndInGenome', 'MeanStability',
                        'MeanIdentity(%)', 'Strand', 'Rule', 'Score', 'Nt(bp)', 'Class',
                        'MidPoint', 'Center', 'TFO sequence', 'TTS sequence',
                    )
                    score = '100'
                    if a.mode == 'fast-experimental':
                        score = '99' if scenario in {'mismatch', 'fallback'} else '100'
                    if a.mode == 'verified' and scenario == 'lying_fallback':
                        score = '98'
                    values = (
                        '1', '60', '1', '60', 'R', 'chr1', '100', '159', '10.0',
                        '90.0', 'ParaPlus', '0', score, '60', '1', '30', '30',
                        'A' * 60, 'T' * 60,
                    )
                    content = '\\t'.join(columns) + '\\n' + '\\t'.join(values) + '\\n'
                    raw_output = output / 'synthetic.TFOsorted.tsv'
                    raw_output.write_text(content, encoding='utf-8')
                    (output / 'argv.json').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')
                fallback = a.mode == 'verified' and scenario in {
                    'fallback', 'mismatch', 'candidate_failure', 'oom', 'comparator_failure',
                    'lying_fallback', 'nested_disagreement'
                }
                if a.mode == 'verified':
                    if scenario in {'fallback', 'mismatch', 'lying_fallback', 'nested_disagreement'}:
                        verified_status, comparator_kind = 'cpu_fallback_after_mismatch', 'mismatch'
                    elif scenario in {'candidate_failure', 'oom'}:
                        verified_status, comparator_kind = 'cpu_fallback_after_candidate_failure', 'not_run'
                    elif scenario == 'comparator_failure':
                        verified_status, comparator_kind = 'cpu_fallback_after_comparator_failure', 'failed'
                    else:
                        verified_status, comparator_kind = 'candidate_clean', 'clean'
                else:
                    verified_status, comparator_kind = 'NA', 'not_run'
                result_status = (
                    'candidate_failure' if failed else
                    'authority_complete' if a.mode == 'cpu-authority' else
                    'experimental_unverified' if a.mode == 'fast-experimental' else
                    verified_status
                )
                published_source = None if failed else (
                    'authority' if a.mode == 'cpu-authority' or fallback else 'candidate'
                )
                published_outputs = []
                if not failed:
                    published_outputs = [
                        output_report(path, output)
                        for path in sorted(output.rglob('*')) if path.is_file()
                    ]
                report = {
                    'schema_version': '1.0.0', 'software_version': 'fake-1',
                    'wrapper_commit': '0' * 40, 'paper_runtime_commit': '0' * 40,
                    'mode': a.mode,
                    'requested_contract': a.contract,
                    'resolved_contract': 'experimental-native' if a.mode == 'fast-experimental' else 'all-ranked-top5',
                    'resolved_execution': a.mode,
                    'result_status': result_status,
                    'authority_backend': str(Path(a.authority_binary).resolve()),
                    'candidate_backend': str(Path(a.candidate_binary).resolve()),
                    'inputs': {'query': input_report(a.query), 'target': input_report(a.target)},
                    'biological_metadata': {'assembly': a.assembly, 'annotation_release': a.annotation_release},
                    'environment': {
                        'platform': 'fake', 'cpu_model': 'fake', 'cpu_thread_count': 1,
                        'gpu_count': 1, 'gpus': [], 'worker_density': 1,
                        'minimum_gpu_memory_mib': 24000, 'checked_compute_capability': '8.9',
                        'cuda_toolkit': 'fake',
                    },
                    'command': [sys.executable, __file__, *sys.argv[1:]],
                    'relevant_environment': {},
                    'timestamps': {'start_utc': 'fake-start', 'end_utc': 'fake-end', 'wall_seconds': 0.01},
                    'backends': {'authority': None, 'candidate': None},
                    'comparators': comparator_report(comparator_kind),
                    'counters': {
                        'fallback': 1 if fallback else 0,
                        'oom': 1 if scenario == 'oom' and failed else 0,
                        'timeout': 0,
                        'guard': 0,
                    },
                    'preflight': {'passed': True, 'checks': {}, 'gpu_ineligibility_reasons': []},
                    'planned_commands': [],
                    'published_source': published_source,
                    'published_outputs': published_outputs,
                    'warnings': [],
                    'errors': ['out of memory'] if scenario == 'oom' and failed else [],
                }
                mutation = os.environ.get('FAKE_REPORT_MUTATION', '')
                if mutation == 'mode': report['mode'] = 'safe'
                elif mutation == 'contract': report['requested_contract'] = 'full-output'
                elif mutation == 'input_path': report['inputs']['query']['path'] = '/wrong/query.fa'
                elif mutation == 'input_digest': report['inputs']['query']['sha256'] = '0' * 64
                elif mutation == 'authority_binary': report['authority_backend'] = '/wrong/authority'
                elif mutation == 'candidate_binary': report['candidate_backend'] = '/wrong/candidate'
                elif mutation == 'source': report['published_source'] = 'authority' if published_source == 'candidate' else 'candidate'
                elif mutation == 'status': report['result_status'] = 'candidate_clean'
                elif mutation == 'fallback_bool': report['counters']['fallback'] = True
                elif mutation == 'guard_float': report['counters']['guard'] = 1.0
                elif mutation == 'oom_string': report['counters']['oom'] = '1'
                elif mutation == 'timeout_missing': del report['counters']['timeout']
                elif mutation == 'fallback_negative': report['counters']['fallback'] = -1
                elif mutation == 'published_output_missing' and a.mode == 'verified':
                    report['published_outputs'].pop()
                elif mutation == 'published_output_fake' and a.mode == 'verified':
                    report['published_outputs'].append({
                        'path': str((output / 'fake.tsv').resolve()),
                        'relative_path': 'fake.tsv',
                        'size_bytes': 0,
                        'sha256': '0' * 64,
                        'record_count': 0,
                    })
                elif mutation == 'published_output_tampered' and a.mode == 'verified':
                    report['published_outputs'][0]['sha256'] = '0' * 64
                Path(a.report).write_text(json.dumps(report, sort_keys=True) + '\\n', encoding='utf-8')
                print('workflow-stdout:' + a.mode)
                print('workflow-stderr:' + a.mode, file=sys.stderr)
                raise SystemExit(9 if failed else 0)
                """
            ),
            encoding="utf-8",
        )
        self.comparator.write_text(
            textwrap.dedent(
                """\
                import argparse, csv, os
                from pathlib import Path

                p = argparse.ArgumentParser()
                p.add_argument('--baseline', required=True)
                p.add_argument('--candidate', required=True)
                p.add_argument('--k', required=True)
                p.add_argument('--details', required=True)
                a = p.parse_args()
                scenario = os.environ.get('FAKE_HOLDOUT_SCENARIO', 'success')
                mutation = os.environ.get('FAKE_COMPARATOR_MUTATION', '')
                details_header = (
                    'side\\tkind\\tmode\\trank\\tcluster_id\\tQueryStart\\tQueryEnd\\t'
                    'StartInSeq\\tEndInSeq\\tDirection\\tChr\\tStartInGenome\\tEndInGenome\\t'
                    'MeanStability\\tMeanIdentity(%)\\tStrand\\tRule\\tScore\\tNt(bp)\\tClass\\t'
                    'MidPoint\\tCenter\\tTFO sequence\\tTTS sequence\\n'
                )
                def read_source(path):
                    with Path(path).open(newline='', encoding='utf-8') as handle:
                        reader = csv.DictReader(handle, delimiter='\\t')
                        return list(reader.fieldnames or []), next(reader)
                baseline_fields, baseline_row = read_source(a.baseline)
                candidate_fields, candidate_row = read_source(a.candidate)
                if mutation == 'malformed_details':
                    Path(a.details).write_text('side\\tkind\\n', encoding='utf-8')
                elif mutation != 'missing_details':
                    rows = []
                    if mutation != 'empty_details':
                        for side, source_row in (
                            ('baseline', baseline_row), ('candidate', candidate_row)
                        ):
                            for mode in ('score', 'stability', 'nt'):
                                rows.append({
                                    'side': side, 'kind': 'raw', 'mode': mode,
                                    'rank': 1, 'cluster_id': 'NA', **source_row,
                                })
                                rows.append({
                                    'side': side, 'kind': 'clustered', 'mode': mode,
                                    'rank': 1, 'cluster_id': 1, **source_row,
                                })
                    if mutation == 'wrong_details':
                        rows[0]['Score'] = '-999'
                    with Path(a.details).open('w', newline='', encoding='utf-8') as handle:
                        writer = csv.DictWriter(
                            handle,
                            fieldnames=['side', 'kind', 'mode', 'rank', 'cluster_id', *baseline_fields],
                            delimiter='\\t',
                            lineterminator='\\n',
                        )
                        writer.writeheader()
                        writer.writerows(rows)
                mismatch = Path(a.baseline).read_text() != Path(a.candidate).read_text()
                diagnostic_only = scenario == 'diagnostic_only'
                inconsistent_rc0 = scenario == 'inconsistent_rc0'
                declared_equal = 0 if mismatch or inconsistent_rc0 else 1
                diagnostic_equal = 0 if mismatch or diagnostic_only or inconsistent_rc0 else 1
                values = {
                    'baseline_rows': 1, 'candidate_rows': 1,
                    'baseline_unique_rows': 1, 'candidate_unique_rows': 1,
                    'full_missing_rows': diagnostic_equal ^ 1,
                    'full_extra_rows': diagnostic_equal ^ 1,
                    'raw_score_top5_equal': diagnostic_equal,
                    'raw_stability_top5_equal': diagnostic_equal,
                    'raw_nt_top5_equal': diagnostic_equal,
                    'clustered_score_top5_equal': declared_equal,
                    'clustered_stability_top5_equal': declared_equal,
                    'clustered_nt_top5_equal': declared_equal,
                    'all_three_top5_equal': declared_equal,
                    'boundary_ties_equal': declared_equal,
                    'baseline_boundary_tie_groups': 0,
                    'candidate_boundary_tie_groups': 0,
                    'representative_conflict_clusters': 0,
                    'candidate_representative_conflict_clusters': 0,
                }
                if mutation == 'negative_count': values['full_missing_rows'] = -1
                if mutation == 'invalid_binary': values['raw_score_top5_equal'] = 2
                if mutation == 'rc_mismatch': values['full_missing_rows'] = 1
                print('baseline=' + a.baseline)
                print('candidate=' + a.candidate)
                for key, value in values.items(): print(f'{key}={value}')
                print('comparator-stderr', file=__import__('sys').stderr)
                if scenario == 'comparator_failure': raise SystemExit(7)
                if diagnostic_only or mismatch: raise SystemExit(1)
                raise SystemExit(0)
                """
            ),
            encoding="utf-8",
        )
        self.environment_capture.write_text(
            textwrap.dedent(
                """\
                import argparse, json
                from pathlib import Path
                p = argparse.ArgumentParser(); p.add_argument('--output', required=True); a = p.parse_args()
                Path(a.output).write_text(json.dumps({'schema_version': 1, 'source': 'fake'}) + '\\n')
                """
            ),
            encoding="utf-8",
        )
    def execute(
        self,
        scenario: str = "success",
        timeouts: dict[str, float] | None = None,
        report_mutation: str | None = None,
        comparator_mutation: str | None = None,
    ):
        environment = {"FAKE_HOLDOUT_SCENARIO": scenario}
        if report_mutation is not None:
            environment["FAKE_REPORT_MUTATION"] = report_mutation
        if comparator_mutation is not None:
            environment["FAKE_COMPARATOR_MUTATION"] = comparator_mutation
        with mock.patch.dict("os.environ", environment):
            return self.runner.execute_attempt(
                attempt=self.attempt,
                manifest=self.manifest,
                destination_parent=self.destination_parent,
                tools=self.tools,
                resume=False,
                outer_timeouts=timeouts,
            )

    def test_success_retains_exact_commands_measurements_outputs_and_receipts(self) -> None:
        result = self.execute()
        run_dir = Path(result["attempt_dir"])
        required = {
            "attempt-config.json",
            "environment.json",
            "comparison.json",
            "attempt-summary.json",
            "attempt-artifacts.tsv",
            "attempt-complete.json",
            "comparator/details.tsv",
            "comparator/stdout.log",
            "comparator/stderr.log",
        }
        for mode in ("authority", "candidate", "verified"):
            required.update(
                {
                    f"{mode}/report.json",
                    f"{mode}/stdout.log",
                    f"{mode}/stderr.log",
                    f"{mode}/time.txt",
                    f"{mode}/gpu-memory.csv",
                    f"{mode}/output/synthetic.TFOsorted.tsv",
                }
            )
        observed = {str(path.relative_to(run_dir)) for path in run_dir.rglob("*") if path.is_file()}
        self.assertTrue(required <= observed, sorted(required - observed))
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        config = json.loads((run_dir / "attempt-config.json").read_text())
        self.assertEqual(summary["outcome"], "complete")
        self.assertEqual(
            set(config["tools"]),
            {
                "workflow",
                "comparator",
                "environment_capture",
                "authority_binary",
                "candidate_binary",
            },
        )
        self.assertEqual(config["runner"]["path"], str(RUNNER.resolve()))
        self.assertEqual(config["runner"]["sha256"], sha256(RUNNER))
        self.assertRegex(config["git_head"], r"^[0-9a-f]{40}$")
        self.assertEqual([row["mode"] for row in summary["mode_results"]], list(self.runner.MODES))
        for row in summary["mode_results"]:
            command = row["command"]
            query_arg = command[command.index("--query") + 1]
            target_arg = command[command.index("--target") + 1]
            self.assertIn("execution-snapshot/inputs/query.fa", query_arg)
            self.assertIn("execution-snapshot/inputs/target.fa", target_arg)
            self.assertNotIn(str(self.query), command)
            self.assertNotIn(str(self.target), command)
            self.assertIn("execution-snapshot/repository/scripts/gasal2_longtarget.py", command[1])
            self.assertIn("--rule", command)
            self.assertIn("0", command)
            self.assertIn("--top-k", command)
            self.assertIn("5", command)
            self.assertIn("GRCh38", command)
            self.assertIn("GENCODE v49", command)
            self.assertIn("--authority-binary", command)
            self.assertTrue(
                any(value.endswith("execution-snapshot/binaries/fasim_longtarget_x86") for value in command)
            )
            self.assertIn("--candidate-binary", command)
            self.assertTrue(
                any(value.endswith("execution-snapshot/binaries/fasim_longtarget_gasal2") for value in command)
            )
            self.assertIn("--comparator", command)
            self.assertTrue(
                any(
                    value.endswith(
                        "execution-snapshot/repository/scripts/compare_fasim_segmented_contract.py"
                    )
                    for value in command
                )
            )
            self.assertEqual(row["report_validation_status"], "valid")
        self.assertFalse((self.work / "SHOULD_NOT_EXIST").exists())

        comparison = json.loads((run_dir / "comparison.json").read_text())
        self.assertIn("authority/output", comparison["baseline_path"])
        self.assertIn("candidate/output", comparison["candidate_path"])
        self.assertNotIn("verified/output", comparison["baseline_path"])
        self.assertEqual(comparison["comparator_returncode"], 0)
        self.assertEqual(comparison["status"], "clean")

        with (run_dir / "attempt-artifacts.tsv").open(newline="", encoding="utf-8") as handle:
            artifact_rows = list(csv.DictReader(handle, delimiter="\t"))
        artifact_paths = {row["artifact_path"] for row in artifact_rows}
        retained_before_receipt = observed - {"attempt-artifacts.tsv", "attempt-complete.json"}
        self.assertEqual(artifact_paths, retained_before_receipt)
        for row in artifact_rows:
            self.assertEqual(row["sha256"], sha256(run_dir / row["artifact_path"]))
        receipt = json.loads((run_dir / "attempt-complete.json").read_text())
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["artifact_manifest_sha256"], sha256(run_dir / "attempt-artifacts.tsv"))
        self.assertEqual(receipt["config_sha256"], sha256(run_dir / "attempt-config.json"))

    def test_scientific_mismatch_is_complete_and_preserved(self) -> None:
        result = self.execute("mismatch")
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        comparison = json.loads((run_dir / "comparison.json").read_text())
        self.assertEqual(summary["outcome"], "scientific_mismatch")
        self.assertEqual(comparison["status"], "mismatch")
        self.assertEqual(comparison["comparator_returncode"], 1)
        self.assertEqual(comparison["metrics"]["full_missing_rows"], 1)
        self.assertTrue((run_dir / "candidate/output/synthetic.TFOsorted.tsv").is_file())

    def test_rc1_diagnostic_differences_can_be_declared_contract_clean(self) -> None:
        result = self.execute("diagnostic_only")
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        comparison = json.loads((run_dir / "comparison.json").read_text())
        self.assertEqual(summary["outcome"], "complete")
        self.assertEqual(comparison["status"], "clean")
        self.assertTrue(comparison["declared_contract_clean"])
        self.assertEqual(comparison["comparator_returncode"], 1)
        self.assertEqual(comparison["metrics"]["full_missing_rows"], 1)
        self.assertEqual(comparison["metrics"]["full_extra_rows"], 1)
        self.assertEqual(comparison["metrics"]["raw_score_top5_equal"], 0)
        self.assertEqual(comparison["metrics"]["clustered_score_top5_equal"], 1)
        self.assertEqual(comparison["metrics"]["clustered_stability_top5_equal"], 1)
        self.assertEqual(comparison["metrics"]["clustered_nt_top5_equal"], 1)
        self.assertEqual(comparison["metrics"]["boundary_ties_equal"], 1)

    def test_rc0_with_failed_declared_gate_is_technical_failure(self) -> None:
        result = self.execute("inconsistent_rc0")
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        comparison = json.loads((run_dir / "comparison.json").read_text())
        self.assertEqual(summary["outcome"], "technical_failure")
        self.assertEqual(comparison["status"], "technical_failure")
        self.assertEqual(comparison["comparator_returncode"], 0)
        self.assertFalse(comparison["declared_contract_clean"])
        self.assertEqual(comparison["reason"], "comparator_returncode_truth_mismatch")

    def test_invalid_comparator_metrics_truth_or_details_are_technical(self) -> None:
        mutations = (
            "negative_count",
            "invalid_binary",
            "rc_mismatch",
            "missing_details",
            "malformed_details",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.destination_parent = self.work / f"artifacts/comparator-{mutation}"
                result = self.execute(comparator_mutation=mutation)
                run_dir = Path(result["attempt_dir"])
                summary = json.loads((run_dir / "attempt-summary.json").read_text())
                comparison = json.loads((run_dir / "comparison.json").read_text())
                self.assertEqual(summary["outcome"], "technical_failure")
                self.assertEqual(comparison["status"], "technical_failure")
                self.assertIn("comparator_failure", summary["failure_reasons"])
                self.assertTrue((run_dir / "comparator/details.tsv").exists())

    def test_comparator_details_must_be_complete_and_bound_to_source_rows(self) -> None:
        for mutation in ("empty_details", "wrong_details"):
            with self.subTest(mutation=mutation):
                self.destination_parent = self.work / f"artifacts/comparator-{mutation}"
                result = self.execute(comparator_mutation=mutation)
                run_dir = Path(result["attempt_dir"])
                summary = json.loads((run_dir / "attempt-summary.json").read_text())
                comparison = json.loads((run_dir / "comparison.json").read_text())
                self.assertEqual(summary["outcome"], "technical_failure")
                self.assertEqual(comparison["status"], "technical_failure")
                self.assertIn("invalid_comparator_details", comparison["reason"])
                self.assertIn("comparator_failure", summary["failure_reasons"])
                self.assertTrue((run_dir / "verified/report.json").is_file())

    def test_candidate_and_comparator_failures_do_not_suppress_verified(self) -> None:
        for scenario, reason in (("candidate_failure", "mode_failure"), ("comparator_failure", "comparator_failure")):
            with self.subTest(scenario=scenario):
                self.destination_parent = self.work / f"artifacts/{scenario}"
                result = self.execute(scenario)
                run_dir = Path(result["attempt_dir"])
                summary = json.loads((run_dir / "attempt-summary.json").read_text())
                self.assertEqual(summary["outcome"], "technical_failure")
                self.assertIn(reason, summary["failure_reasons"])
                self.assertTrue((run_dir / "verified/report.json").is_file())
                self.assertTrue((run_dir / "verified/stdout.log").is_file())

    def test_malformed_or_misbound_mode_reports_are_technical_and_all_modes_continue(self) -> None:
        mutations = (
            "mode",
            "contract",
            "input_path",
            "input_digest",
            "authority_binary",
            "candidate_binary",
            "source",
            "status",
            "fallback_bool",
            "guard_float",
            "oom_string",
            "timeout_missing",
            "fallback_negative",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.destination_parent = self.work / f"artifacts/report-{mutation}"
                result = self.execute(report_mutation=mutation)
                summary = json.loads(
                    (Path(result["attempt_dir"]) / "attempt-summary.json").read_text()
                )
                self.assertEqual(summary["outcome"], "technical_failure")
                self.assertIn("mode_report_invalid", summary["failure_reasons"])
                self.assertEqual(len(summary["mode_results"]), 3)
                self.assertTrue(
                    any(
                        row["report_validation_status"] == "invalid"
                        for row in summary["mode_results"]
                    )
                )

    def test_verified_candidate_clean_requires_exact_published_output_evidence(self) -> None:
        for mutation in (
            "published_output_missing",
            "published_output_fake",
            "published_output_tampered",
        ):
            with self.subTest(mutation=mutation):
                self.destination_parent = self.work / f"artifacts/report-{mutation}"
                result = self.execute(report_mutation=mutation)
                run_dir = Path(result["attempt_dir"])
                summary = json.loads((run_dir / "attempt-summary.json").read_text())
                by_mode = {row["mode"]: row for row in summary["mode_results"]}
                self.assertEqual(summary["outcome"], "technical_failure")
                self.assertEqual(by_mode["cpu-authority"]["report_validation_status"], "valid")
                self.assertEqual(by_mode["fast-experimental"]["report_validation_status"], "valid")
                self.assertEqual(by_mode["verified"]["report_validation_status"], "invalid")
                self.assertTrue((run_dir / "verified/output/synthetic.TFOsorted.tsv").is_file())
                self.assertTrue((run_dir / "verified/output/argv.json").is_file())

    def test_timeout_oom_and_verified_fallback_are_explicit(self) -> None:
        cases = (
            ("timeout", {mode: 1.0 for mode in self.runner.MODES}, "timeout_count"),
            ("oom", None, "oom_count"),
            ("fallback", None, "fallback_count"),
        )
        cases[0][1]["cpu-authority"] = 0.1
        for scenario, timeouts, field in cases:
            with self.subTest(scenario=scenario):
                self.destination_parent = self.work / f"artifacts/{scenario}"
                result = self.execute(scenario, timeouts)
                run_dir = Path(result["attempt_dir"])
                summary = json.loads((run_dir / "attempt-summary.json").read_text())
                self.assertGreater(summary[field], 0)
                self.assertEqual(len(summary["mode_results"]), 3)
                self.assertTrue((run_dir / "verified/stderr.log").is_file())
                if scenario in {"timeout", "oom"}:
                    self.assertEqual(summary["outcome"], "technical_failure")
                else:
                    self.assertEqual(summary["verified_result_status"], "cpu_fallback_after_mismatch")

    def test_sampler_failures_are_unavailable_and_do_not_abort_modes(self) -> None:
        header = (
            "timestamp,measurement_status,gpu_index,memory_used_mib,memory_total_mib,"
            "utilization_gpu_percent,temperature_gpu_c,power_draw_w,clocks_sm_mhz\n"
        )

        class StartFailureSampler:
            def __init__(self, path): self.path = path
            def start(self): raise RuntimeError("sampler start failure")
            def stop(self): pass

        class StopFailureSampler:
            def __init__(self, path): self.path = path
            def start(self): self.path.write_text(header, encoding="utf-8")
            def stop(self): raise SystemExit("sampler stop failure")

        class MissingOutputSampler:
            def __init__(self, path): self.path = path
            def start(self): pass
            def stop(self): pass

        for label, sampler in (
            ("start", StartFailureSampler),
            ("stop", StopFailureSampler),
            ("async-output", MissingOutputSampler),
        ):
            with self.subTest(label=label):
                self.destination_parent = self.work / f"artifacts/sampler-{label}"
                with mock.patch.object(self.runner, "GpuSampler", sampler):
                    try:
                        result = self.execute()
                    except BaseException as exc:
                        self.fail(f"sampler {label} aborted attempt: {type(exc).__name__}: {exc}")
                run_dir = Path(result["attempt_dir"])
                summary = json.loads((run_dir / "attempt-summary.json").read_text())
                self.assertEqual(len(summary["mode_results"]), 3)
                self.assertTrue((run_dir / "verified/report.json").is_file())
                self.assertTrue(
                    all(
                        not row.get("gpu_telemetry_available", True)
                        for row in summary["mode_results"]
                    )
                )
                self.assertTrue(
                    all(row["telemetry_errors"] for row in summary["mode_results"])
                )

    def test_missing_and_invalid_time_evidence_is_explicitly_unavailable(self) -> None:
        evidence = getattr(
            self.runner,
            "time_evidence",
            lambda _path, attempted: {
                "time_telemetry_available": True,
                "time_telemetry_status": "available",
                "time_telemetry_reason": "unchecked",
                "max_rss_kb": 0,
            },
        )
        missing = evidence(self.work / "missing-time.txt", attempted=True)
        self.assertFalse(missing["time_telemetry_available"])
        self.assertEqual(missing["max_rss_kb"], "NA")
        invalid_path = self.work / "invalid-time.txt"
        invalid_path.write_text("Maximum resident set size (kbytes): nope\n", encoding="utf-8")
        invalid = evidence(invalid_path, attempted=True)
        self.assertFalse(invalid["time_telemetry_available"])
        self.assertEqual(invalid["max_rss_kb"], "NA")

    def test_lying_verified_fallback_artifact_is_technical_and_retained(self) -> None:
        result = self.execute("lying_fallback")
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        evidence_path = run_dir / "verified-evidence/comparison.json"
        self.assertTrue(evidence_path.is_file())
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual(summary["outcome"], "technical_failure")
        self.assertIn("verified_fallback_artifact_mismatch", summary["failure_reasons"])
        self.assertEqual(evidence["status"], "mismatch")
        self.assertGreater(evidence["metrics"]["full_missing_rows"], 0)
        for relative in ("details.tsv", "stdout.log", "stderr.log", "comparison.json"):
            self.assertTrue((run_dir / "verified-evidence" / relative).is_file())

    def test_nested_verified_comparator_disagreement_is_explicit_instability(self) -> None:
        result = self.execute("nested_disagreement")
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        comparison = json.loads((run_dir / "comparison.json").read_text())
        self.assertEqual(comparison["status"], "clean")
        self.assertEqual(summary["outcome"], "scientific_instability")
        self.assertFalse(summary["direct_vs_verified_declared_contract_consistent"])
        self.assertIn(
            "verified_direct_contract_disagreement", summary["failure_reasons"]
        )


class HoldoutOrchestrationTests(HoldoutAttemptExecutionTests):
    def fake_plan(self, count: int = 36) -> dict[str, object]:
        pilot = dict(self.attempt)
        pilot.update(
            attempt_id="pilot__hq01_ht01__repeat00",
            workload_id="hq01_ht01",
            query_id="hq01",
        )
        attempts = []
        for index in range(count):
            attempt = dict(self.attempt)
            workload_id = f"fake{index:02d}_ht01"
            attempt.update(
                attempt_id=f"{workload_id}__repeat00",
                workload_id=workload_id,
                repeat_index=0,
            )
            attempts.append(attempt)
        return {
            "schema_version": 1,
            "freeze_id": EXPECTED_FREEZE_ID,
            "manifest_sha256": sha256(self.manifest),
            "workload_count": count,
            "formal_attempt_count": count,
            "top_level_run_count": count * 3,
            "backend_execution_count": count * 4,
            "pilot": pilot,
            "formal_attempts": attempts,
        }

    def test_modes_are_mutually_exclusive_and_formal_has_no_subset_option(self) -> None:
        parser = self.runner.parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--artifact-root",
                    str(self.work / "artifacts"),
                    "--pilot",
                    "--formal",
                ]
            )
        option_strings = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        self.assertNotIn("--workload-id", option_strings)
        self.assertNotIn("--query-id", option_strings)
        self.assertNotIn("--gene-id", option_strings)

    def test_cli_defaults_to_canonical_root_and_rejects_external_execution_root(self) -> None:
        expected_root = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
        parser = self.runner.parser()
        self.assertEqual(parser.get_default("artifact_root"), expected_root)

        external = self.work / "external execution root"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(self.runner, "build_plan", return_value=self.fake_plan(1)) as build, mock.patch.object(
            self.runner, "run_pilot", return_value={"status": "executed"}
        ) as run_pilot, mock.patch.object(
            sys,
            "argv",
            ["run_holdout.py", "--pilot", "--artifact-root", str(external)],
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = self.runner.main()
        self.assertEqual(returncode, 2)
        self.assertIn("canonical", stderr.getvalue())
        self.assertIn(str(expected_root), stderr.getvalue())
        build.assert_not_called()
        run_pilot.assert_not_called()

    def test_attempt_config_changes_with_git_head(self) -> None:
        original = self.runner.attempt_config(self.attempt, self.manifest, self.tools)
        with mock.patch.object(
            self.runner, "git_head", return_value="0" * 40, create=True
        ):
            drifted = self.runner.attempt_config(self.attempt, self.manifest, self.tools)
        self.assertNotEqual(original["config_digest_sha256"], drifted["config_digest_sha256"])
        self.assertEqual(drifted["git_head"], "0" * 40)

    def _assert_mid_attempt_drift(self, label, mutate, mutate_after="authority") -> None:
        destination_parent = self.work / f"drift artifacts/{label}"
        launched = []
        original = self.runner._run_mode

        def run_then_mutate(namespace, *args, **kwargs):
            launched.append(namespace)
            result = original(namespace, *args, **kwargs)
            if namespace == mutate_after:
                mutate()
            return result

        with mock.patch.object(self.runner, "_run_mode", side_effect=run_then_mutate):
            with self.assertRaisesRegex(ValueError, "identity|drift|digest|SHA"):
                self.runner.execute_attempt(
                    attempt=self.attempt,
                    manifest=self.manifest,
                    destination_parent=destination_parent,
                    tools=self.tools,
                    resume=False,
                )
        expected_modes = ["authority", "candidate", "verified"]
        self.assertEqual(launched, expected_modes[: expected_modes.index(mutate_after) + 1])
        self.assertFalse((destination_parent / self.attempt["attempt_id"]).exists())
        partials = list(destination_parent.glob(f".{self.attempt['attempt_id']}.partial.*"))
        self.assertEqual(len(partials), 1)
        self.assertTrue((partials[0] / "attempt-config.json").is_file())
        self.assertFalse(any("retry" in path.name for path in destination_parent.iterdir()))

    def test_mid_attempt_input_drift_preserves_partial_and_blocks_later_modes(self) -> None:
        self._assert_mid_attempt_drift(
            "input", lambda: self.query.write_text(">q\nTTTTTTTT\n", encoding="ascii")
        )

    def test_mid_attempt_tool_drift_preserves_partial_and_blocks_later_modes(self) -> None:
        original = self.workflow.read_bytes()
        self._assert_mid_attempt_drift(
            "tool", lambda: self.workflow.write_bytes(original + b"\n# tool drift\n")
        )

    def test_mid_attempt_head_drift_preserves_partial_and_blocks_later_modes(self) -> None:
        state = {"drifted": False}
        original_head = self.runner.git_head()

        def observed_head():
            return "0" * 40 if state["drifted"] else original_head

        with mock.patch.object(self.runner, "git_head", side_effect=observed_head):
            self._assert_mid_attempt_drift(
                "head", lambda: state.update(drifted=True), mutate_after="verified"
            )

    def test_transient_input_replacement_launches_only_snapshot_bytes(self) -> None:
        original_run = self.runner._run_captured
        raced = False

        def run_with_race(command, *args, **kwargs):
            nonlocal raced
            if not raced and "--mode" in command and "cpu-authority" in command:
                raced = True
                original = self.query.read_bytes()
                self.query.write_text(">wrong\nTTTTTTTT\n", encoding="ascii")
                try:
                    return original_run(command, *args, **kwargs)
                finally:
                    self.query.write_bytes(original)
            return original_run(command, *args, **kwargs)

        with mock.patch.object(self.runner, "_run_captured", side_effect=run_with_race):
            result = self.execute()
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        authority = next(row for row in summary["mode_results"] if row["mode"] == "cpu-authority")
        authority_report = json.loads((run_dir / "authority/report.json").read_text())
        self.assertTrue(raced)
        self.assertEqual(summary["outcome"], "complete")
        self.assertEqual(authority_report["inputs"]["query"]["sha256"], self.attempt["query_file_sha256"])
        self.assertIn("execution-snapshot", authority_report["inputs"]["query"]["path"])
        self.assertIn("execution-snapshot", authority["command"][1])
        snapshot_query = run_dir / "execution-snapshot/inputs/query.fa"
        self.assertEqual(sha256(snapshot_query), self.attempt["query_file_sha256"])
        with (run_dir / "attempt-artifacts.tsv").open(newline="", encoding="utf-8") as handle:
            artifacts = {row["artifact_path"]: row for row in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(artifacts["execution-snapshot/inputs/query.fa"]["sha256"], sha256(snapshot_query))

    def test_transient_tool_replacement_launches_only_snapshot_bytes(self) -> None:
        original_run = self.runner._run_captured
        marker = self.work / "wrong-workflow-executed"
        raced = False
        replacement = (
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('wrong tool ran')\n"
            "raise SystemExit(91)\n"
        ).encode("utf-8")

        def run_with_race(command, *args, **kwargs):
            nonlocal raced
            if not raced and "--mode" in command and "cpu-authority" in command:
                raced = True
                original = self.workflow.read_bytes()
                self.workflow.write_bytes(replacement)
                try:
                    return original_run(command, *args, **kwargs)
                finally:
                    self.workflow.write_bytes(original)
            return original_run(command, *args, **kwargs)

        with mock.patch.object(self.runner, "_run_captured", side_effect=run_with_race):
            result = self.execute()
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        authority = next(row for row in summary["mode_results"] if row["mode"] == "cpu-authority")
        self.assertTrue(raced)
        self.assertFalse(marker.exists())
        self.assertEqual(summary["outcome"], "complete")
        self.assertIn("execution-snapshot", authority["command"][1])
        snapshot_workflow = run_dir / "execution-snapshot/repository/scripts/gasal2_longtarget.py"
        self.assertEqual(sha256(snapshot_workflow), sha256(self.workflow))

    def test_attempt_publication_rechecks_identity_inside_publisher(self) -> None:
        original_publish = self.runner._publish_attempt_receipt
        original_workflow = self.workflow.read_bytes()

        def publish_with_race(*args, **kwargs):
            self.workflow.write_bytes(original_workflow + b"\n# publication race\n")
            try:
                return original_publish(*args, **kwargs)
            finally:
                self.workflow.write_bytes(original_workflow)

        with mock.patch.object(
            self.runner, "_publish_attempt_receipt", side_effect=publish_with_race
        ):
            with self.assertRaisesRegex(ValueError, "identity|drift|SHA"):
                self.runner.execute_attempt(
                    attempt=self.attempt,
                    manifest=self.manifest,
                    destination_parent=self.destination_parent,
                    tools=self.tools,
                    resume=False,
                )
        destination = self.destination_parent / self.attempt["attempt_id"]
        self.assertFalse(destination.exists())
        partials = list(self.destination_parent.glob(f".{self.attempt['attempt_id']}.partial.*"))
        self.assertEqual(len(partials), 1)
        self.assertTrue((partials[0] / "attempt-complete.json").is_file())

    def test_formal_table_publication_rechecks_identity_inside_publisher(self) -> None:
        artifact_root = self.work / "formal publication race"
        plan = self.fake_plan(1)
        self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        self.runner.run_formal(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        identity = self.runner.capture_plan_execution_identity(plan, self.manifest, self.tools)
        before = {
            name: (artifact_root / name).read_bytes()
            for name in self.runner.FORMAL_TABLE_NAMES
        }
        drifted_plan = dict(plan)
        drifted_plan["freeze_id"] = "wrong-epoch"
        original_publish = self.runner.publish_formal_tables_transactionally
        original_workflow = self.workflow.read_bytes()

        def publish_with_race(*args, **kwargs):
            self.workflow.write_bytes(original_workflow + b"\n# table publication race\n")
            try:
                return original_publish(*args, **kwargs)
            finally:
                self.workflow.write_bytes(original_workflow)

        with mock.patch.object(
            self.runner,
            "publish_formal_tables_transactionally",
            side_effect=publish_with_race,
        ):
            with self.assertRaisesRegex(ValueError, "identity|drift|SHA"):
                self.runner.rebuild_formal_tables(
                    plan=drifted_plan,
                    manifest=self.manifest,
                    artifact_root=artifact_root,
                    tools=self.tools,
                    execution_identity=identity,
                )
        self.assertEqual(
            {name: (artifact_root / name).read_bytes() for name in self.runner.FORMAL_TABLE_NAMES},
            before,
        )
        self.assertFalse(any(path.name.startswith(".formal-tables.transaction.") for path in artifact_root.iterdir()))

    def test_pilot_and_formal_configs_share_one_pinned_execution_identity(self) -> None:
        artifact_root = self.work / "common identity artifacts"
        plan = self.fake_plan(2)
        self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        self.runner.run_formal(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        config_paths = [
            artifact_root / "pilot/pilot__hq01_ht01__repeat00/attempt-config.json",
            *[
                artifact_root / "formal" / attempt["attempt_id"] / "attempt-config.json"
                for attempt in plan["formal_attempts"]
            ],
        ]
        configs = [json.loads(path.read_text()) for path in config_paths]
        for config in configs:
            self.assertIn("execution_identity", config)
            self.assertIn("execution_identity_sha256", config)
        self.assertEqual(len({config["execution_identity_sha256"] for config in configs}), 1)
        self.assertTrue(all(config["execution_identity"] == configs[0]["execution_identity"] for config in configs))
        bindings = configs[0]["execution_identity"]["inputs"]
        self.assertEqual(bindings[self.attempt["query_path"]]["file_sha256"], self.attempt["query_file_sha256"])
        self.assertEqual(bindings[self.attempt["query_path"]]["sequence_sha256"], self.attempt["query_sequence_sha256"])
        self.assertEqual(bindings[self.attempt["target_path"]]["file_sha256"], self.attempt["target_file_sha256"])
        self.assertEqual(bindings[self.attempt["target_path"]]["sequence_sha256"], self.attempt["target_sequence_sha256"])
        for config in configs:
            for field in (
                "query_file_sha256",
                "query_sequence_sha256",
                "target_file_sha256",
                "target_sequence_sha256",
            ):
                self.assertEqual(config["attempt"][field], self.attempt[field])

    def test_plan_execution_identity_rejects_manifest_binding_drift(self) -> None:
        plan = self.fake_plan(1)
        plan["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "manifest.*drift|drift.*manifest"):
            self.runner.capture_plan_execution_identity(plan, self.manifest, self.tools)

    def test_dirty_production_checkout_is_rejected_before_plan_or_execution(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(
            self.runner,
            "production_checkout_changes",
            return_value=["?? untracked-result"],
            create=True,
        ), mock.patch.object(
            self.runner, "build_plan", return_value=self.fake_plan(1)
        ) as build, mock.patch.object(
            self.runner, "run_pilot", return_value={"status": "executed"}
        ) as run_pilot, mock.patch.object(
            sys, "argv", ["run_holdout.py", "--pilot"]
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = self.runner.main()
        self.assertEqual(returncode, 2)
        self.assertIn("clean", stderr.getvalue())
        self.assertIn("untracked-result", stderr.getvalue())
        build.assert_not_called()
        run_pilot.assert_not_called()

    def test_execution_marker_detection_includes_local_partial_and_config(self) -> None:
        canonical = self.work / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
        partial = canonical / "formal/.fake00_ht01__repeat00.partial.12345"
        partial.mkdir(parents=True)
        config = canonical / "pilot/pilot__hq01_ht01__repeat00/attempt-config.json"
        config.parent.mkdir(parents=True)
        config.write_text("{}\n", encoding="utf-8")
        detector = getattr(self.runner, "execution_start_markers", lambda _root: [])
        markers = detector(canonical)
        rendered = {str(path.relative_to(canonical)) for path in markers}
        self.assertIn("formal/.fake00_ht01__repeat00.partial.12345", rendered)
        self.assertIn("pilot/pilot__hq01_ht01__repeat00/attempt-config.json", rendered)

    def test_pilot_is_fixed_separate_and_formal_refuses_without_valid_receipt(self) -> None:
        artifact_root = self.work / "holdout artifacts"
        plan = self.fake_plan(2)
        with self.assertRaisesRegex(ValueError, "pilot"):
            self.runner.run_formal(
                plan=plan,
                manifest=self.manifest,
                artifact_root=artifact_root,
                tools=self.tools,
                resume=False,
            )
        self.assertFalse((artifact_root / "formal").exists())
        pilot = self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        self.assertEqual(pilot["attempt_id"], "pilot__hq01_ht01__repeat00")
        self.assertTrue(
            (artifact_root / "pilot/pilot__hq01_ht01__repeat00/attempt-complete.json").is_file()
        )
        self.assertFalse((artifact_root / "formal").exists())

    def test_formal_represents_all_36_mismatches_and_rebuilds_receipt_tables(self) -> None:
        artifact_root = self.work / "formal artifacts"
        plan = self.fake_plan(36)
        self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        with mock.patch.dict("os.environ", {"FAKE_HOLDOUT_SCENARIO": "mismatch"}):
            result = self.runner.run_formal(
                plan=plan,
                manifest=self.manifest,
                artifact_root=artifact_root,
                tools=self.tools,
                resume=False,
            )
        self.assertTrue(result["complete_representation"])
        self.assertEqual(result["represented_attempt_count"], 36)
        with (artifact_root / "formal-attempts.tsv").open(newline="", encoding="utf-8") as handle:
            attempt_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(attempt_rows), 36)
        self.assertEqual({row["attempt_id"] for row in attempt_rows}, {row["attempt_id"] for row in plan["formal_attempts"]})
        self.assertEqual({row["outcome"] for row in attempt_rows}, {"scientific_mismatch"})
        with (artifact_root / "formal-failures.tsv").open(newline="", encoding="utf-8") as handle:
            failure_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(failure_rows), 36)
        self.assertEqual({row["failure_type"] for row in failure_rows}, {"scientific_mismatch"})
        with (artifact_root / "formal-artifacts.tsv").open(newline="", encoding="utf-8") as handle:
            artifact_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertGreater(len(artifact_rows), 36)
        summary = json.loads((artifact_root / "formal-summary.json").read_text())
        self.assertEqual(summary["planned_attempt_count"], 36)
        self.assertEqual(summary["represented_attempt_count"], 36)
        self.assertEqual(summary["outcome_counts"], {"scientific_mismatch": 36})
        self.assertFalse(any("retry" in path.name for path in (artifact_root / "formal").iterdir()))

    def test_resume_reuses_only_checksum_valid_complete_attempt(self) -> None:
        artifact_root = self.work / "resume artifacts"
        plan = self.fake_plan(1)
        first = self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        run_dir = Path(first["attempt_dir"])
        expected_config = self.runner.attempt_config(plan["pilot"], self.manifest, self.tools)
        reused = self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=True,
        )
        self.assertEqual(reused["status"], "reused")
        with self.assertRaisesRegex(ValueError, "already exists|duplicate"):
            self.runner.run_pilot(
                plan=plan,
                manifest=self.manifest,
                artifact_root=artifact_root,
                tools=self.tools,
                resume=False,
            )

        for relative in (
            "attempt-config.json",
            "authority/report.json",
            "candidate/output/synthetic.TFOsorted.tsv",
            "attempt-complete.json",
        ):
            with self.subTest(relative=relative):
                path = run_dir / relative
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "tamper|checksum|digest|canonical|artifact"):
                    self.runner.validate_attempt_receipt(run_dir, expected_config)
                path.write_bytes(original)
                self.runner.validate_attempt_receipt(run_dir, expected_config)

    def test_unexpected_mode_exception_is_retained_and_other_modes_continue(self) -> None:
        original = self.runner._run_mode
        calls = []

        def fail_authority_once(namespace, *args, **kwargs):
            calls.append(namespace)
            if namespace == "authority":
                raise RuntimeError("synthetic unexpected exception")
            return original(namespace, *args, **kwargs)

        with mock.patch.object(self.runner, "_run_mode", side_effect=fail_authority_once):
            result = self.runner.execute_attempt(
                attempt=self.attempt,
                manifest=self.manifest,
                destination_parent=self.work / "exception artifacts",
                tools=self.tools,
                resume=False,
            )
        run_dir = Path(result["attempt_dir"])
        summary = json.loads((run_dir / "attempt-summary.json").read_text())
        self.assertEqual(calls, ["authority", "candidate", "verified"])
        self.assertEqual(summary["outcome"], "technical_failure")
        self.assertIn("mode_exception", summary["failure_reasons"])
        self.assertTrue((run_dir / "attempt-complete.json").is_file())
        self.assertTrue((run_dir / "verified/report.json").is_file())

    def test_execute_attempt_fails_closed_on_stale_partial_without_launching(self) -> None:
        destination_parent = self.work / "stale direct artifacts"
        destination_parent.mkdir(parents=True)
        stale = destination_parent / f".{self.attempt['attempt_id']}.partial.999999"
        stale.mkdir()
        marker = stale / "produced-before-crash.bin"
        marker.write_bytes(b"\x00stale-primary-bytes\xff")
        before = marker.read_bytes()
        with mock.patch.object(
            self.runner, "_run_mode", wraps=self.runner._run_mode
        ) as run_mode:
            with self.assertRaisesRegex(ValueError, "stale.*partial|partial.*adjudication"):
                self.runner.execute_attempt(
                    attempt=self.attempt,
                    manifest=self.manifest,
                    destination_parent=destination_parent,
                    tools=self.tools,
                    resume=False,
                )
        run_mode.assert_not_called()
        self.assertEqual(marker.read_bytes(), before)
        self.assertFalse((destination_parent / self.attempt["attempt_id"]).exists())

    def test_formal_resume_preflights_all_stale_partials_without_launching(self) -> None:
        artifact_root = self.work / "stale formal artifacts"
        plan = self.fake_plan(1)
        self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        self.runner.run_formal(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        attempt_id = plan["formal_attempts"][0]["attempt_id"]
        stale = artifact_root / "formal" / f".{attempt_id}.partial.424242"
        stale.mkdir()
        marker = stale / "stdout.log"
        marker.write_bytes(b"partial output must survive exactly\n")
        before = marker.read_bytes()
        with mock.patch.object(self.runner, "_run_mode") as run_mode:
            with self.assertRaisesRegex(ValueError, "stale.*partial|partial.*adjudication"):
                self.runner.run_formal(
                    plan=plan,
                    manifest=self.manifest,
                    artifact_root=artifact_root,
                    tools=self.tools,
                    resume=True,
                )
        run_mode.assert_not_called()
        self.assertEqual(marker.read_bytes(), before)

    def test_receipt_rejects_in_tree_artifact_symlink_without_changing_target(self) -> None:
        result = self.execute()
        run_dir = Path(result["attempt_dir"])
        authority_raw = run_dir / "authority/output/synthetic.TFOsorted.tsv"
        candidate_raw = run_dir / "candidate/output/synthetic.TFOsorted.tsv"
        target_before = candidate_raw.read_bytes()
        authority_raw.unlink()
        authority_raw.symlink_to(candidate_raw)
        expected_config = self.runner.attempt_config(self.attempt, self.manifest, self.tools)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.runner.validate_attempt_receipt(run_dir, expected_config)
        self.assertEqual(candidate_raw.read_bytes(), target_before)
        self.assertTrue(authority_raw.is_symlink())

    def test_formal_rejects_symlinked_pilot_attempt_directory(self) -> None:
        artifact_root = self.work / "symlinked pilot artifacts"
        plan = self.fake_plan(1)
        result = self.runner.run_pilot(
            plan=plan,
            manifest=self.manifest,
            artifact_root=artifact_root,
            tools=self.tools,
            resume=False,
        )
        pilot_dir = Path(result["attempt_dir"])
        external = self.work / "external preserved pilot"
        pilot_dir.rename(external)
        receipt_before = (external / "attempt-complete.json").read_bytes()
        pilot_dir.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink|contain"):
            self.runner.run_formal(
                plan=plan,
                manifest=self.manifest,
                artifact_root=artifact_root,
                tools=self.tools,
                resume=False,
            )
        self.assertEqual((external / "attempt-complete.json").read_bytes(), receipt_before)
        self.assertFalse((artifact_root / "formal").exists())

    def test_canonical_artifact_root_rejects_symlinked_components(self) -> None:
        validator = getattr(
            self.runner,
            "validate_artifact_root_components",
            lambda _root, _trusted: None,
        )
        real_parent = self.work / "real-parent"
        real_parent.mkdir()
        linked_parent = self.work / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        through_parent = linked_parent / "canonical"
        through_parent.mkdir()
        with self.assertRaisesRegex(ValueError, "symlink"):
            validator(through_parent, self.work)

        real_root = self.work / "real-root"
        real_root.mkdir()
        linked_root = self.work / "linked-root"
        linked_root.symlink_to(real_root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            validator(linked_root, self.work)
        self.assertEqual(list(real_root.iterdir()), [])

    def test_run_captured_kills_and_reaps_process_group_on_baseexception(self) -> None:
        child = self.work / "fake tools/long child.py"
        pid_path = self.work / "child.pid"
        child.write_text(
            "import os,sys,time\n"
            "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        original_wait = subprocess.Popen.wait
        injected = False

        def interrupt_once(process, *args, **kwargs):
            nonlocal injected
            if not injected:
                deadline = time.time() + 3
                while not pid_path.exists() and time.time() < deadline:
                    time.sleep(0.01)
                injected = True
                raise KeyboardInterrupt("synthetic interrupt")
            return original_wait(process, *args, **kwargs)

        with mock.patch.object(subprocess.Popen, "wait", new=interrupt_once):
            with self.assertRaises(KeyboardInterrupt):
                self.runner._run_captured(
                    [sys.executable, str(child), str(pid_path)],
                    self.work / "child.stdout",
                    self.work / "child.stderr",
                    10,
                )
        self.assertTrue(pid_path.is_file())
        pid = int(pid_path.read_text())
        alive = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            alive = False
        finally:
            if alive:
                os.kill(pid, 9)
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
        self.assertFalse(alive, f"interrupted child process remained alive: {pid}")

    def test_environment_capture_kills_and_reaps_process_group_on_baseexception(self) -> None:
        partial = self.work / "environment partial"
        partial.mkdir()
        pid_path = partial / "environment.pid"
        self.environment_capture.write_text(
            "import subprocess,sys,time\n"
            "from pathlib import Path\n"
            "output = Path(sys.argv[sys.argv.index('--output') + 1])\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            "output.with_name('environment.pid').write_text(str(child.pid))\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        identity = self.runner.capture_execution_identity(
            self.manifest, self.tools, [self.attempt]
        )
        snapshot = self.runner.create_execution_snapshot(
            partial, self.attempt, identity
        )
        original_communicate = subprocess.Popen.communicate
        injected = False

        def interrupt_once(process, *args, **kwargs):
            nonlocal injected
            if not injected:
                deadline = time.time() + 3
                while not pid_path.exists() and time.time() < deadline:
                    time.sleep(0.01)
                injected = True
                raise KeyboardInterrupt("synthetic environment interrupt")
            return original_communicate(process, *args, **kwargs)

        with mock.patch.object(
            subprocess.Popen, "communicate", new=interrupt_once
        ), mock.patch.object(subprocess.Popen, "__exit__", return_value=None):
            with self.assertRaises(KeyboardInterrupt):
                self.runner._capture_environment(partial, snapshot, identity)
        self.assertTrue(pid_path.is_file())
        pid = int(pid_path.read_text())
        running = True
        try:
            status = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
            running = status[status.rfind(")") + 2] != "Z"
        except FileNotFoundError:
            running = False
        finally:
            if running:
                os.kill(pid, 9)
        self.assertFalse(running, f"interrupted environment capture remained alive: {pid}")

    def test_attempt_publication_rejects_nested_symlink_before_rename(self) -> None:
        partial = self.work / ".symlinked.partial.1"
        destination = self.work / "published-attempt"
        nested = partial / "nested"
        nested.mkdir(parents=True)
        external = self.work / "external.bin"
        external.write_bytes(b"external bytes stay unchanged\n")
        before = external.read_bytes()
        (nested / "linked.bin").symlink_to(external)
        identity = self.runner.capture_execution_identity(
            self.manifest, self.tools, [self.attempt]
        )
        snapshot = self.runner.create_execution_snapshot(
            partial, self.attempt, identity
        )
        self.runner.write_json(partial / "attempt-config.json", {"schema_version": 1})
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.runner._publish_attempt_receipt(
                partial,
                destination,
                {"config_digest_sha256": "0" * 64},
                {"attempt_id": "symlinked", "outcome": "technical_failure"},
                identity,
                snapshot,
            )
        self.assertFalse(destination.exists())
        self.assertTrue(partial.is_dir())
        self.assertTrue((nested / "linked.bin").is_symlink())
        self.assertEqual(external.read_bytes(), before)

    def test_attempt_publication_recursively_fsyncs_nested_files_and_directories(self) -> None:
        original_fsync = os.fsync
        observed: set[str] = set()

        def record_fsync(fd):
            try:
                observed.add(os.readlink(f"/proc/self/fd/{fd}"))
            except OSError:
                pass
            return original_fsync(fd)

        with mock.patch.object(os, "fsync", side_effect=record_fsync):
            self.execute()
        self.assertTrue(
            any(path.endswith("authority/output/synthetic.TFOsorted.tsv") for path in observed),
            sorted(observed),
        )
        self.assertTrue(any(path.endswith("comparator/details.tsv") for path in observed))
        self.assertTrue(any(path.endswith("authority/output") for path in observed))
        self.assertTrue(any(".synthetic_ht01__repeat00.partial." in path for path in observed))

    def test_formal_table_set_rolls_back_exactly_after_each_replace(self) -> None:
        names = (
            "formal-attempts.tsv",
            "formal-failures.tsv",
            "formal-artifacts.tsv",
            "formal-summary.json",
        )
        publisher = getattr(
            self.runner,
            "publish_formal_tables_transactionally",
            None,
        )
        self.assertIsNotNone(publisher)
        for failure_index in range(1, 5):
            with self.subTest(failure_index=failure_index):
                root = self.work / f"formal-transaction-{failure_index}"
                root.mkdir()
                before = {}
                outputs = {}
                for index, name in enumerate(names, start=1):
                    before[name] = f"old-{index}\n".encode()
                    outputs[name] = f"new-{index}\n".encode()
                    (root / name).write_bytes(before[name])

                def fail_after_replace(index, _name):
                    if index == failure_index:
                        raise RuntimeError(f"injected replace {index}")

                with self.assertRaisesRegex(RuntimeError, "injected replace"):
                    publisher(root, outputs, after_replace=fail_after_replace)
                self.assertEqual(
                    {name: (root / name).read_bytes() for name in names}, before
                )
                debris = [
                    path.name
                    for path in root.iterdir()
                    if path.name not in names
                ]
                self.assertEqual(debris, [])


class HoldoutPreexecutionIntegrationTests(unittest.TestCase):
    def test_make_target_checker_and_submission_manifest_are_complete(self) -> None:
        checker_path = ROOT / "scripts/check_bioinformatics_phase2_preexecution.sh"
        self.assertTrue(checker_path.is_file(), f"missing checker: {checker_path}")
        checker = checker_path.read_text(encoding="utf-8")
        for phrase in (
            "check_analyze_bioinformatics_frozen_contracts.py",
            "check_run_bioinformatics_holdout.py",
            "holdout_execution_started=0",
            "workload=24",
            "attempts=36",
            "top_level=108",
            "backend=144",
            "attempt-complete.json",
            "attempt-config.json",
            ".partial.",
            "bioinformatics-phase2-holdout-v1",
            "execution_start_markers",
        ):
            with self.subTest(checker_phrase=phrase):
                self.assertIn(phrase, checker)

        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "check-bioinformatics-phase2-preexecution: check-bioinformatics-phase2-freeze",
            makefile,
        )
        self.assertIn("bash ./scripts/check_bioinformatics_phase2_preexecution.sh", makefile)

        fields, rows = read_manifest(ROOT / "paper/bioinformatics/submission_manifest.tsv")
        self.assertEqual(
            fields,
            [
                "artifact_id",
                "path",
                "phase",
                "artifact_class",
                "authority",
                "freeze_or_epoch",
                "required",
                "status",
            ],
        )
        by_path = {row["path"]: row for row in rows}
        expected_paths = {
            "paper/bioinformatics/frozen_contract_matrix.tsv",
            "paper/bioinformatics/mismatch_feature_matrix.tsv",
            "paper/bioinformatics/mismatch_analysis.md",
            "reproduce/bioinformatics/analyze_frozen_contracts.py",
            "tests/check_analyze_bioinformatics_frozen_contracts.py",
            "paper/bioinformatics/holdout_execution_protocol.md",
            "reproduce/bioinformatics/run_holdout.py",
            "tests/check_run_bioinformatics_holdout.py",
            "scripts/check_bioinformatics_phase2_preexecution.sh",
        }
        self.assertTrue(expected_paths <= set(by_path), sorted(expected_paths - set(by_path)))
        for path in expected_paths:
            self.assertEqual(by_path[path]["phase"], "2")
            self.assertEqual(by_path[path]["status"], "pass")

    def test_repository_contains_no_pilot_or_formal_attempt_receipt(self) -> None:
        canonical = ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
        self.assertFalse(canonical.exists(), f"canonical execution root exists: {canonical}")
        receipts = []
        for path in ROOT.rglob("attempt-complete.json"):
            relative = path.relative_to(ROOT)
            if "pilot" in relative.parts or "formal" in relative.parts:
                receipts.append(str(relative))
        self.assertEqual(receipts, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
