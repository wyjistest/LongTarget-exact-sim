#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "characterize_fasim_segment_ownership_h19.py"


def metrics(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


class SegmentOwnershipH19RunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="fasim-phase2-h19-runner-")
        self.work = Path(self.tempdir.name)
        self.query = self.work / "query.fa"
        self.target = self.work / "target.fa"
        self.query.write_text(">H19-test\n" + "A" * 30 + "\n", encoding="utf-8")
        self.target.write_text(">test|chr1|1-100\n" + "C" * 100 + "\n", encoding="utf-8")
        self.binary = self.work / "fake-fasim.py"
        self.binary.write_text(
            textwrap.dedent(
                r'''
                #!/usr/bin/env python3
                import csv
                import re
                import sys
                from pathlib import Path

                columns = (
                    "QueryStart", "QueryEnd", "StartInSeq", "EndInSeq", "Direction",
                    "Chr", "StartInGenome", "EndInGenome", "MeanStability",
                    "MeanIdentity(%)", "Strand", "Rule", "Score", "Nt(bp)", "Class",
                    "MidPoint", "Center", "TFO sequence", "TTS sequence",
                )
                args = sys.argv[1:]
                query = Path(args[args.index("-f2") + 1])
                output = Path(args[args.index("-O") + 1])
                header = query.read_text(encoding="utf-8").splitlines()[0]
                match = re.search(r"global_query_start=(\d+)\|global_query_end=(\d+)", header)
                start, end = (int(match.group(1)), int(match.group(2))) if match else (0, 30)
                global_rows = [(1, 4, 300), (13, 15, 200), (27, 30, 100)]
                output.mkdir(parents=True, exist_ok=True)
                path = output / "fixture-TFOsorted"
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
                    writer.writeheader()
                    for index, (query_start, query_end, score) in enumerate(global_rows, 1):
                        if start <= query_start - 1 and query_end <= end:
                            local_start = query_start - start
                            local_end = query_end - start
                            midpoint = (local_start + local_end) // 2
                            writer.writerow({
                                "QueryStart": local_start, "QueryEnd": local_end,
                                "StartInSeq": index * 10, "EndInSeq": index * 10 + 60,
                                "Direction": "R", "Chr": "chr1",
                                "StartInGenome": index * 100, "EndInGenome": index * 100 + 60,
                                "MeanStability": index, "MeanIdentity(%)": 75,
                                "Strand": "ParaPlus", "Rule": 0, "Score": score,
                                "Nt(bp)": 60 + index, "Class": 0,
                                "MidPoint": midpoint, "Center": midpoint,
                                "TFO sequence": f"TFO{index}", "TTS sequence": f"TTS{index}",
                            })
                print("benchmark.fasim_gasal2_requests=0", file=sys.stderr)
                print("benchmark.fasim_gasal2_traceback_requests=0", file=sys.stderr)
                '''
            ).lstrip(),
            encoding="utf-8",
        )
        self.binary.chmod(0o755)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_three_shift_clean_fixture_produces_complete_gate_receipt(self) -> None:
        run_work = self.work / "run"
        environment = os.environ.copy()
        environment.update(
            {
                "BIN": str(self.binary),
                "WORK": str(run_work),
                "TARGET": str(self.target),
                "RNA": str(self.query),
                "SEGMENT_LEN": "16",
                "SEGMENT_OVERLAP": "4",
                "GRID_SHIFTS": "0 2 4",
                "FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW": "1",
            }
        )
        result = subprocess.run(
            ["python3", str(RUNNER)],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        values = metrics(run_work / "summary.txt")
        self.assertEqual(values["authority_rows"], "3")
        self.assertEqual(values["grid_shift_count"], "3")
        self.assertEqual(values["short_oracle_missing_rows"], "0")
        self.assertEqual(values["short_oracle_extra_rows"], "0")
        self.assertEqual(values["all_three_top5_equal"], "1")
        self.assertEqual(values["boundary_ties_equal"], "1")
        self.assertEqual(values["multiple_shift_matrix_clean"], "1")
        self.assertEqual(values["potential_exact_tasks_removed"], "unavailable")
        self.assertEqual(values["potential_tracebacks_removed"], "unavailable")
        self.assertEqual(values["runtime_work_dropped"], "0")
        self.assertEqual(values["phase2_decision"], "pass")
        self.assertTrue((run_work / "matrix.tsv").is_file())
        self.assertTrue((run_work / "dual-grid" / "contract.txt").is_file())
        for shift in (0, 2, 4):
            grid = run_work / "grids" / f"shift_{shift}"
            self.assertTrue((grid / "merged-TFOsorted").is_file())
            self.assertTrue((grid / "ownership-TFOsorted").is_file())
            self.assertTrue((grid / "merged-contract.txt").is_file())
            self.assertTrue((grid / "ownership-contract.txt").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
