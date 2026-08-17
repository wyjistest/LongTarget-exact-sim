#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh"


def parse_metrics(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class SegmentedArchiveRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase1-runner-")
        self.work = Path(self.tempdir.name)
        self.target = self.work / "target.fa"
        self.query = self.work / "query.fa"
        self.target.write_text(
            ">hg19|chr11|1000-1063\n" + "ACGT" * 16 + "\n",
            encoding="utf-8",
        )
        self.query.write_text(">KCNQ1OT1-test\n" + "AACCGGTT" * 10 + "\n", encoding="utf-8")
        self.fake_binary = self.work / "fake-fasim"
        self.fake_binary.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                [[ "${FASIM_OUTPUT_MODE:-}" == "tfosorted" ]]
                [[ "${FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT:-}" == "1" ]]
                if [[ "${FAKE_EXPECT_EXACT:-0}" == "1" ]]; then
                  [[ "${FASIM_EXACT_COLUMN_SCOREINFO_GPU:-}" == "1" ]]
                  [[ "${FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK:-}" == "512" ]]
                  [[ "${FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT:-}" == "1" ]]
                  [[ "${FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT:-}" == "0" ]]
                  [[ "${FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW:-}" == "0" ]]
                fi
                printf 'run\\n' >>"${FAKE_INVOCATION_LOG:?}"
                out_dir=""
                while (($#)); do
                  case "$1" in
                    -O) out_dir="$2"; shift 2 ;;
                    *) shift ;;
                  esac
                done
                mkdir -p "$out_dir"
                printf 'FATFOC1\\000\\002\\000\\000\\000\\000\\000\\001\\000\\000\\000\\000\\000' \
                  >"$out_dir/segment-TFOsorted.archive-first.tfoa"
                if [[ "${FAKE_DUPLICATE_ARCHIVE:-0}" == "1" ]]; then
                  cp "$out_dir/segment-TFOsorted.archive-first.tfoa" \
                    "$out_dir/duplicate-TFOsorted.archive-first.tfoa"
                fi
                if [[ "${FAKE_EMIT_FULL_TEXT:-0}" == "1" ]]; then
                  printf 'QueryStart\\tQueryEnd\\tStartInSeq\\tEndInSeq\\tDirection\\tChr\\tStartInGenome\\tEndInGenome\\tMeanStability\\tMeanIdentity(%%)\\tStrand\\tRule\\tScore\\tNt(bp)\\tClass\\tMidPoint\\tCenter\\tTFO sequence\\tTTS sequence\\n' \
                    >"$out_dir/segment-TFOsorted"
                fi
                exact_enabled="${FASIM_EXACT_COLUMN_SCOREINFO_GPU:-0}"
                column_tasks=$((10 * (1 - exact_enabled)))
                scoreinfo_tasks=$((10 * exact_enabled))
                column_wall=0.2
                scoreinfo_wall=0.0
                if [[ "$exact_enabled" == "1" ]]; then
                  column_wall=0.0
                  scoreinfo_wall=0.1
                fi
                printf '%s\\n' \
                  'benchmark.fasim_gasal2_archive_first_output_requested=1' \
                  'benchmark.fasim_gasal2_archive_first_output_active=1' \
                  'benchmark.fasim_gasal2_archive_first_output_decision=active' \
                  'benchmark.fasim_gasal2_requests=0' \
                  'benchmark.fasim_gasal2_traceback_requests=0' \
                  'benchmark.fasim_gasal2_fallbacks=0' \
                  'benchmark.fasim_gasal2_length_guard_fallbacks=0' \
                  "benchmark.fasim_top5_gasal2_phase_exact_column_tasks=$column_tasks" \
                  "benchmark.fasim_top5_gasal2_phase_exact_column_cells=$((column_tasks * 100))" \
                  "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds=$column_wall" \
                  "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks=$scoreinfo_tasks" \
                  "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells=$((scoreinfo_tasks * 100))" \
                  "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=$scoreinfo_wall" \
                  "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled=$exact_enabled" \
                  'benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled=0' \
                  'benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches=0' \
                  'benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches=0' \
                  'benchmark.fasim_gasal2_traceback_fill_seconds=0.1' \
                  'benchmark.fasim_gasal2_traceback_submit_seconds=0.01' \
                  'benchmark.fasim_gasal2_traceback_wait_seconds=0.2' \
                  'benchmark.fasim_gasal2_cpu_traceback_convert_seconds=0.3' >&2
                """
            ),
            encoding="utf-8",
        )
        self.fake_binary.chmod(0o755)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_runner(
        self,
        label: str,
        *,
        duplicate_archive: bool = False,
        emit_full_text: bool = False,
        clean_archives: bool = False,
        ownership_shadow: bool = False,
        resume: bool = False,
        exact_scoreinfo_pruned: bool = False,
        gasal2_batch: int = 20000,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        run_work = self.work / label
        invocation_log = self.work / f"{label}-invocations.log"
        environment = os.environ.copy()
        environment.update(
            {
                "BIN": str(self.fake_binary),
                "WORK": str(run_work),
                "TARGET": str(self.target),
                "RNA": str(self.query),
                "KCNQ1OT1_FASTA": str(self.query),
                "SEGMENT_LEN": "32",
                "SEGMENT_OVERLAP": "8",
                "GRID_SHIFTS": "0 4",
                "MAX_SEGMENTS": "2",
                "FAKE_DUPLICATE_ARCHIVE": "1" if duplicate_archive else "0",
                "FAKE_EMIT_FULL_TEXT": "1" if emit_full_text else "0",
                "CLEAN_SEGMENT_ARCHIVES_AFTER_MERGE": "1" if clean_archives else "0",
                "FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW": "1" if ownership_shadow else "0",
                "RESUME": "1" if resume else "0",
                "EXACT_SCOREINFO_PRUNED": "1" if exact_scoreinfo_pruned else "0",
                "GASAL2_BATCH": str(gasal2_batch),
                "FAKE_EXPECT_EXACT": "1" if exact_scoreinfo_pruned else "0",
                "FAKE_INVOCATION_LOG": str(invocation_log),
            }
        )
        result = subprocess.run(
            ["bash", str(RUNNER)],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result, run_work

    def test_runner_uses_typed_archive_manifest_sqlite_and_retains_archives(self) -> None:
        result, run_work = self.run_runner("clean")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        manifests = sorted(run_work.glob("grids/shift_*/segment_outputs.tsv"))
        self.assertEqual(len(manifests), 2)
        artifact_paths: list[Path] = []
        for manifest in manifests:
            with manifest.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                self.assertEqual(
                    reader.fieldnames,
                    [
                        "segment_id",
                        "global_start",
                        "global_end",
                        "artifact_kind",
                        "artifact_path",
                        "query_fasta",
                        "query_fasta_sha256",
                        "target_fasta",
                        "target_fasta_sha256",
                    ],
                )
                rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["artifact_kind"] == "archive_first_tfoa" for row in rows))
            self.assertTrue(all(len(row["query_fasta_sha256"]) == 64 for row in rows))
            self.assertTrue(all(len(row["target_fasta_sha256"]) == 64 for row in rows))
            artifact_paths.extend(Path(row["artifact_path"]) for row in rows)
        self.assertTrue(all(path.is_file() for path in artifact_paths))
        self.assertEqual(list(run_work.glob("grids/shift_*/run_*/*-TFOsorted")), [])
        self.assertEqual(list(run_work.glob("grids/shift_*/*.sqlite")), [])

        metrics = parse_metrics(run_work / "summary.txt")
        self.assertEqual(metrics["per_segment_full_text_emitted"], "0")
        self.assertEqual(metrics["bounded_memory_backend_active"], "1")
        self.assertEqual(metrics["segment_archives_retained"], "4")
        self.assertEqual(metrics["gasal2_fallbacks"], "0")
        self.assertEqual(metrics["shift_0_dedup_backend"], "sqlite")
        self.assertEqual(metrics["shift_4_dedup_backend"], "sqlite")
        self.assertEqual(metrics["segment_ownership_shadow_requested"], "0")
        self.assertEqual(metrics["segment_ownership_shadow_active"], "0")
        self.assertEqual(metrics["segment_ownership_runtime_work_dropped"], "0")
        self.assertEqual(metrics["exact_scoreinfo_gpu_pruned_output_enabled"], "0")
        self.assertEqual(metrics["exact_work_tasks"], "40")
        self.assertEqual(metrics["exact_work_cells"], "4000")
        self.assertEqual(metrics["exact_stage_seconds"], "0.800000")
        self.assertEqual(metrics["traceback_host_observed_stage_seconds"], "2.440000")
        self.assertEqual(list(run_work.glob("grids/shift_*/ownership-*")), [])
        self.assertIn("pipeline_wall_seconds", metrics)

    def test_explicit_ownership_shadow_is_bounded_and_does_not_replace_merged_output(self) -> None:
        result, run_work = self.run_runner("ownership", ownership_shadow=True)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        metrics = parse_metrics(run_work / "summary.txt")
        self.assertEqual(metrics["segment_ownership_shadow_requested"], "1")
        self.assertEqual(metrics["segment_ownership_shadow_active"], "1")
        self.assertEqual(metrics["segment_ownership_runtime_work_dropped"], "0")
        self.assertEqual(metrics["segment_ownership_potential_exact_tasks_removed"], "unavailable")
        self.assertEqual(metrics["segment_ownership_potential_tracebacks_removed"], "unavailable")
        for shift in (0, 4):
            grid = run_work / "grids" / f"shift_{shift}"
            self.assertTrue((grid / "ownership-descriptors.tsv").is_file())
            self.assertTrue((grid / "ownership-shadow.sqlite").is_file())
            self.assertTrue((grid / "ownership-shadow-TFOsorted").is_file())
            self.assertTrue((grid / "ownership-shadow-summary.txt").is_file())
            self.assertTrue((grid / "merged-common-TFOsorted").is_file())

    def test_runner_rejects_multiple_archives(self) -> None:
        result, _run_work = self.run_runner("duplicate", duplicate_archive=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one", result.stderr.lower())

    def test_runner_rejects_full_segment_text(self) -> None:
        result, _run_work = self.run_runner("full-text", emit_full_text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("full segment tfosorted", result.stderr.lower())

    def test_runner_cleans_archives_only_when_explicitly_requested(self) -> None:
        result, run_work = self.run_runner("cleanup", clean_archives=True)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(list(run_work.glob("grids/shift_*/run_*/*.archive-first.tfoa")), [])
        metrics = parse_metrics(run_work / "summary.txt")
        self.assertEqual(metrics["segment_archives_retained"], "0")
        self.assertGreater(int(metrics["archive_input_bytes"]), 0)

    def test_resume_uses_config_digest_and_does_not_repeat_completed_segments(self) -> None:
        first, run_work = self.run_runner(
            "resume", resume=True, exact_scoreinfo_pruned=True
        )
        segment_stderr = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in run_work.glob("grids/shift_*/run_*/stderr.log")
        )
        self.assertEqual(
            first.returncode,
            0,
            msg=(
                f"stdout:\n{first.stdout}\nstderr:\n{first.stderr}"
                f"\nsegment stderr:\n{segment_stderr}"
            ),
        )
        invocation_log = self.work / "resume-invocations.log"
        self.assertEqual(invocation_log.read_text(encoding="utf-8").splitlines(), ["run"] * 4)

        config = json.loads((run_work / "run-config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["schema_version"], 1)
        self.assertEqual(config["archive_first"], True)
        self.assertEqual(config["exact_column_variant"], "gpu_pruned_scoreinfo_v1")
        self.assertEqual(config["traceback_certificate_mode"], "disabled")
        self.assertEqual(config["grid_mode"], "dual_grid")
        self.assertEqual(config["worker_count"], 1)
        self.assertEqual(config["keep_dedup_db"], False)
        self.assertEqual(config["clean_segment_archives_after_merge"], False)
        self.assertEqual(len(config["binary_sha256"]), 64)
        self.assertEqual(len(config["query_sha256"]), 64)
        self.assertEqual(len(config["target_sha256"]), 64)
        self.assertEqual(len(config["config_digest_sha256"]), 64)
        self.assertTrue((run_work / "run-complete.json").is_file())
        self.assertEqual(
            len(list(run_work.glob("grids/shift_*/run_*/segment-complete.json"))),
            4,
        )
        summary = parse_metrics(run_work / "summary.txt")
        self.assertEqual(summary["exact_scoreinfo_gpu_pruned_output_enabled"], "1")
        self.assertEqual(summary["exact_work_tasks"], "40")
        self.assertEqual(summary["exact_work_cells"], "4000")
        self.assertEqual(summary["exact_stage_seconds"], "0.400000")

        second, _ = self.run_runner(
            "resume", resume=True, exact_scoreinfo_pruned=True
        )
        self.assertEqual(second.returncode, 0, msg=second.stderr)
        self.assertEqual(invocation_log.read_text(encoding="utf-8").splitlines(), ["run"] * 4)
        self.assertIn("resume_complete=1", second.stdout)

        merged = run_work / "grids" / "shift_0" / "merged-common-TFOsorted"
        merged.unlink()
        rebuilt, _ = self.run_runner(
            "resume", resume=True, exact_scoreinfo_pruned=True
        )
        self.assertEqual(rebuilt.returncode, 0, msg=rebuilt.stderr)
        self.assertTrue(merged.is_file())
        self.assertEqual(invocation_log.read_text(encoding="utf-8").splitlines(), ["run"] * 4)

        mismatch, _ = self.run_runner(
            "resume",
            resume=True,
            exact_scoreinfo_pruned=True,
            gasal2_batch=12345,
        )
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("config digest mismatch", mismatch.stderr.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
