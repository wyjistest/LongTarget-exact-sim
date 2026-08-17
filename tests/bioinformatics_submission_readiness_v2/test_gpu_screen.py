from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/gasal2_gpu_screen.py"
sys.path.insert(0, str(ROOT / "scripts"))
from gasal2_candidate_sites import (  # noqa: E402
    FIELDS,
    CandidateSitesError,
    ProductIdentity,
    build_receipt,
    read_single_fasta,
    schema_descriptor,
    validate_candidate_sites,
)


class GpuScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="gpu-screen-test-")
        self.work = Path(self.temporary.name)
        self.query = self.work / "query.fa"
        self.target = self.work / "target.fa"
        self.query.write_text(">query-id\n" + "A" * 100 + "\n", encoding="ascii")
        self.target.write_text(">target-id\n" + "A" * 200 + "\n", encoding="ascii")
        self.output = self.work / "output"
        self.report = self.work / "report.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def backend(self, *, fallback: int = 0, empty: bool = False) -> Path:
        path = self.work / f"backend-{fallback}-{int(empty)}.py"
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import os
                import sys
                from pathlib import Path
                output = Path(sys.argv[sys.argv.index('-O') + 1])
                marker = os.environ.get('GPU_SCREEN_TEST_MARKER')
                if marker:
                    Path(marker).write_text('candidate-only\\n', encoding='ascii')
                columns = {list(FIELDS)!r}
                native = [
                    'QueryStart','QueryEnd','StartInSeq','EndInSeq','Direction','Chr',
                    'StartInGenome','EndInGenome','MeanStability','MeanIdentity(%)',
                    'Strand','Rule','Score','Nt(bp)','Class','MidPoint','Center',
                    'TFO sequence','TTS sequence'
                ]
                destination = output / 'test-TFOsorted'
                with destination.open('w', encoding='ascii') as handle:
                    handle.write('\\t'.join(native) + '\\n')
                    if not {empty!r}:
                        row = [
                            '1','61','1','61','R','target-id','0','61','10','100',
                            'ParaPlus','1','100','61','1','31','31','A'*61,'A'*61
                        ]
                        handle.write('\\t'.join(row) + '\\n')
                for line in (
                    'benchmark.fasim_top5_gasal2_gpu_scoreinfo_requested=1',
                    'benchmark.fasim_top5_gasal2_gpu_scoreinfo_active=1',
                    'benchmark.fasim_gasal2_enabled=1',
                    'benchmark.fasim_gasal2_built=1',
                    'benchmark.fasim_gasal2_requests=1',
                    'benchmark.fasim_gasal2_fallbacks={fallback}',
                ):
                    print(line, file=sys.stderr)
                """
            ),
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def environment(
        self,
        marker: Path | None = None,
        runtime_identity: Path | None = None,
    ) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
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
                ),
            }
        )
        if marker is not None:
            environment["GPU_SCREEN_TEST_MARKER"] = str(marker)
        if runtime_identity is not None:
            environment["GASAL2_GPU_SCREEN_RUNTIME_IDENTITY"] = str(runtime_identity)
        return environment

    def run_cli(
        self,
        backend: Path,
        *extra: str,
        marker: Path | None = None,
        runtime_identity: Path | None = None,
    ):
        return subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--query",
                str(self.query),
                "--target",
                str(self.target),
                "--output",
                str(self.output),
                "--report",
                str(self.report),
                "--candidate-binary",
                str(backend),
                *extra,
            ],
            cwd=ROOT,
            env=self.environment(marker, runtime_identity),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )

    def test_candidate_only_success_writes_versioned_sites(self) -> None:
        marker = self.work / "candidate-started"
        result = self.run_cli(self.backend(), marker=marker)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(marker.read_text().strip(), "candidate-only")
        sites = self.output / "candidate_sites.tsv"
        summary = validate_candidate_sites(sites)
        self.assertEqual(summary["row_count"], 3)
        with sites.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual([row["ranking_mode"] for row in rows], ["score", "stability", "nt"])
        self.assertTrue(all(row["scientific_contract"] == "biological_topk_candidate_site_v1" for row in rows))
        report = json.loads(self.report.read_text())
        self.assertEqual(report["execution_identity"]["execution_mode"], "gpu-screen")
        self.assertEqual(report["execution_identity"]["validation_status"], "pending_phase4")
        self.assertIsNone(report["backend"].get("authority") if isinstance(report["backend"], dict) else None)

    def test_empty_native_output_is_header_only_product(self) -> None:
        result = self.run_cli(self.backend(empty=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = validate_candidate_sites(self.output / "candidate_sites.tsv")
        self.assertTrue(summary["header_only"])
        self.assertEqual(summary["row_count"], 0)

    def test_fallback_fails_without_product_output(self) -> None:
        result = self.run_cli(self.backend(fallback=1))
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertFalse(self.output.exists())
        report = json.loads(self.report.read_text())
        self.assertEqual(report["result_status"], "unexpected_fallback")

    def test_query_envelope_fails_before_backend(self) -> None:
        self.query.write_text(">query-id\n" + "A" * 2813 + "\n", encoding="ascii")
        marker = self.work / "candidate-started"
        result = self.run_cli(self.backend(), marker=marker)
        self.assertEqual(result.returncode, 3)
        self.assertFalse(marker.exists())
        self.assertFalse(self.output.exists())

    def test_candidate_sites_are_byte_deterministic(self) -> None:
        first = self.run_cli(self.backend())
        self.assertEqual(first.returncode, 0, first.stderr)
        payload = (self.output / "candidate_sites.tsv").read_bytes()
        second_output = self.work / "output-2"
        second_report = self.work / "report-2.json"
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--query",
                str(self.query),
                "--target",
                str(self.target),
                "--output",
                str(second_output),
                "--report",
                str(second_report),
                "--candidate-binary",
                str(self.backend()),
            ],
            cwd=ROOT,
            env=self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload, (second_output / "candidate_sites.tsv").read_bytes())

    def test_runtime_identity_environment_default_is_bound(self) -> None:
        backend = self.backend()
        identity_path = self.work / "runtime_identity.json"
        identity_path.write_text(
            json.dumps(
                {
                    "execution_mode": "gpu-screen",
                    "scientific_contract": "biological_topk_candidate_site_v1",
                    "output_schema": "gasal2_candidate_sites_tsv_v1",
                    "software_epoch": "submission_rc_v2_2",
                    "implementation_commit": "a" * 40,
                    "candidate_binary_sha256": hashlib.sha256(backend.read_bytes()).hexdigest(),
                    "container_image_digest": "sha256:" + "b" * 64,
                }
            ),
            encoding="utf-8",
        )
        result = self.run_cli(backend, runtime_identity=identity_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.report.read_text())
        self.assertEqual(report["runtime_identity"]["source_commit"], "a" * 40)
        self.assertEqual(
            report["runtime_identity"]["runtime_identity_path"],
            str(identity_path),
        )

    def test_frozen_schema_descriptor_matches_implementation(self) -> None:
        frozen = json.loads(
            (ROOT / "schemas/gasal2_candidate_sites_tsv_v1.schema.json").read_text()
        )
        self.assertEqual(frozen, schema_descriptor())

    def test_candidate_site_digest_is_recomputed(self) -> None:
        result = self.run_cli(self.backend())
        self.assertEqual(result.returncode, 0, result.stderr)
        sites = self.output / "candidate_sites.tsv"
        lines = sites.read_text(encoding="utf-8").splitlines()
        digest_index = lines[0].split("\t").index("candidate_site_identity_digest")
        first = lines[1].split("\t")
        first[digest_index] = "0" * 64
        lines[1] = "\t".join(first)
        sites.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(CandidateSitesError, "identity digest drift"):
            validate_candidate_sites(sites)

    def test_genomic_target_extraction_interval_uses_declared_offset(self) -> None:
        result = self.run_cli(self.backend(), "--target-region-start0", "1000")
        self.assertEqual(result.returncode, 0, result.stderr)
        native = self.output / "diagnostics/native-TFOsorted"
        receipt = build_receipt(
            query=read_single_fasta(self.query, "query"),
            target=read_single_fasta(self.target, "target"),
            tfosorted=native,
            identity=ProductIdentity(target_region_start0=1000),
        )
        self.assertEqual(
            receipt.input_identity["target_extracted_interval"],
            {"start0": 1000, "end0": 1200},
        )


if __name__ == "__main__":
    unittest.main()
