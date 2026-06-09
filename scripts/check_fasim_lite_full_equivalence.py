#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_fasim_lite_full_equivalence.py"


LITE_HEADER = "\t".join(
    [
        "Chr",
        "StartInGenome",
        "EndInGenome",
        "Strand",
        "Rule",
        "QueryStart",
        "QueryEnd",
        "StartInSeq",
        "EndInSeq",
        "Direction",
        "Score",
        "Nt(bp)",
        "MeanIdentity(%)",
        "MeanStability",
    ]
)


TFOSORTED_HEADER = "\t".join(
    [
        "QueryStart",
        "QueryEnd",
        "StartInSeq",
        "EndInSeq",
        "Direction",
        "Chr",
        "StartInGenome",
        "EndInGenome",
        "MeanStability",
        "MeanIdentity(%)",
        "Strand",
        "Rule",
        "Score",
        "Nt(bp)",
        "Class",
        "MidPoint",
        "Center",
        "TFO sequence",
        "TTS sequence",
    ]
)


LITE_ROW_A = "\t".join(
    [
        "chr22",
        "10",
        "30",
        "+",
        "R",
        "1",
        "20",
        "5",
        "25",
        "+",
        "70",
        "18",
        "92.5",
        "41.2",
    ]
)


LITE_ROW_B = "\t".join(
    [
        "chr22",
        "100",
        "130",
        "-",
        "Y",
        "2",
        "24",
        "8",
        "38",
        "-",
        "66",
        "20",
        "88.1",
        "39.9",
    ]
)


LITE_ROW_C = "\t".join(
    [
        "chr22",
        "200",
        "240",
        "+",
        "M",
        "3",
        "28",
        "12",
        "52",
        "+",
        "61",
        "19",
        "87.0",
        "37.5",
    ]
)


TFOSORTED_ROW_A = "\t".join(
    [
        "1",
        "20",
        "5",
        "25",
        "+",
        "chr22",
        "10",
        "30",
        "41.2",
        "92.5",
        "+",
        "R",
        "70",
        "18",
        "triplex",
        "20",
        "18",
        "AAAA",
        "TTTT",
    ]
)


TFOSORTED_ROW_B = "\t".join(
    [
        "2",
        "24",
        "8",
        "38",
        "-",
        "chr22",
        "100",
        "130",
        "39.9",
        "88.1",
        "-",
        "Y",
        "66",
        "20",
        "triplex",
        "115",
        "114",
        "CCCC",
        "GGGG",
    ]
)


TFOSORTED_ROW_C = "\t".join(
    [
        "3",
        "28",
        "12",
        "52",
        "+",
        "chr22",
        "200",
        "240",
        "37.5",
        "87.0",
        "+",
        "M",
        "61",
        "19",
        "triplex",
        "220",
        "218",
        "ACAC",
        "TGTG",
    ]
)


def write_lite(path: Path, rows: list[str]) -> None:
    path.write_text(LITE_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def write_tfosorted(path: Path, rows: list[str]) -> None:
    path.write_text(
        TFOSORTED_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8"
    )


def write_lite_with_header(path: Path, header: str, rows: list[str]) -> None:
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def run_compare(baseline: Path, candidate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_compare_reports(
    baseline_report: Path,
    candidate_report: Path,
    *,
    output_field: str | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--baseline-report",
        str(baseline_report),
        "--candidate-report",
        str(candidate_report),
    ]
    if output_field is not None:
        cmd.extend(["--report-output-field", output_field])
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_report(path: Path, output_path: Path, *, field: str = "merged_output") -> None:
    payload = {field: str(output_path)}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        baseline = tmp / "baseline.lite"
        candidate_same = tmp / "candidate_same.lite"
        candidate_diff = tmp / "candidate_diff.lite"
        candidate_bad_schema = tmp / "candidate_bad_schema.lite"
        candidate_short_row = tmp / "candidate_short_row.lite"
        candidate_long_row = tmp / "candidate_long_row.lite"
        baseline_tfosorted = tmp / "baseline-TFOsorted"
        candidate_tfosorted_same = tmp / "candidate_same-TFOsorted"
        baseline_report = tmp / "baseline_report.json"
        baseline_topk_report = tmp / "baseline_topk_report.json"
        candidate_report = tmp / "candidate_report.json"
        candidate_topk_report = tmp / "candidate_topk_report.json"

        write_lite(baseline, [LITE_ROW_B, LITE_ROW_A, LITE_ROW_A])
        write_lite(candidate_same, [LITE_ROW_A, LITE_ROW_B])
        write_lite(candidate_diff, [LITE_ROW_A, LITE_ROW_C])
        write_tfosorted(
            baseline_tfosorted,
            [TFOSORTED_ROW_B, TFOSORTED_ROW_A, TFOSORTED_ROW_A],
        )
        write_tfosorted(
            candidate_tfosorted_same,
            [TFOSORTED_ROW_A, TFOSORTED_ROW_B],
        )
        write_report(baseline_report, baseline)
        write_report(baseline_topk_report, baseline, field="topk_lite_output")
        write_report(candidate_report, candidate_same)
        write_report(candidate_topk_report, candidate_same, field="topk_lite_output")
        write_lite(candidate_short_row, ["\t".join(LITE_ROW_A.split("\t")[:-1])])
        write_lite(candidate_long_row, [LITE_ROW_A + "\textra"])
        write_lite_with_header(
            candidate_bad_schema,
            "\t".join(LITE_HEADER.split("\t")[:-1]),
            ["\t".join(LITE_ROW_A.split("\t")[:-1])],
        )

        same = run_compare(baseline, candidate_same)
        if same.returncode != 0:
            print(same.stdout)
            print(same.stderr, file=sys.stderr)
            raise SystemExit("expected same full-lite comparison to pass")
        for phrase in (
            "schema=lite",
            "full_rows_equal=true",
            "baseline_rows=3",
            "baseline_unique_rows=2",
            "candidate_unique_rows=2",
            "missing_rows=0",
            "extra_rows=0",
        ):
            if phrase not in same.stdout:
                raise SystemExit(f"same comparison missing phrase: {phrase}")

        same_tfosorted = run_compare(baseline_tfosorted, candidate_tfosorted_same)
        if same_tfosorted.returncode != 0:
            print(same_tfosorted.stdout)
            print(same_tfosorted.stderr, file=sys.stderr)
            raise SystemExit("expected same TFOsorted comparison to pass")
        for phrase in (
            "schema=tfosorted",
            "full_rows_equal=true",
            "baseline_rows=3",
            "candidate_unique_rows=2",
        ):
            if phrase not in same_tfosorted.stdout:
                raise SystemExit(f"TFOsorted comparison missing phrase: {phrase}")

        mixed_schema = run_compare(baseline, candidate_tfosorted_same)
        if mixed_schema.returncode == 0:
            print(mixed_schema.stdout)
            raise SystemExit("expected mixed-schema comparison to fail")
        if "schemas_must_match=true" not in mixed_schema.stdout:
            print(mixed_schema.stdout)
            raise SystemExit("mixed-schema comparison missing schema mismatch detail")

        diff = run_compare(baseline, candidate_diff)
        if diff.returncode == 0:
            print(diff.stdout)
            raise SystemExit("expected different full-lite comparison to fail")
        for phrase in (
            "full_rows_equal=false",
            "missing_rows=1",
            "extra_rows=1",
            "first_missing_row=",
            "first_extra_row=",
        ):
            if phrase not in diff.stdout:
                raise SystemExit(f"diff comparison missing phrase: {phrase}")

        bad_schema = run_compare(baseline, candidate_bad_schema)
        if bad_schema.returncode == 0:
            print(bad_schema.stdout)
            raise SystemExit("expected bad-schema full-lite comparison to fail")
        if "schema_error=" not in bad_schema.stdout:
            print(bad_schema.stdout)
            print(bad_schema.stderr, file=sys.stderr)
            raise SystemExit("bad-schema comparison missing schema_error")
        if "unsupported_schema" not in bad_schema.stdout:
            print(bad_schema.stdout)
            raise SystemExit("bad-schema comparison missing unsupported schema detail")

        for label, malformed_path in (
            ("short-row", candidate_short_row),
            ("long-row", candidate_long_row),
        ):
            malformed = run_compare(baseline, malformed_path)
            if malformed.returncode == 0:
                print(malformed.stdout)
                raise SystemExit(f"expected {label} full-lite comparison to fail")
            if "parse_error=" not in malformed.stdout:
                print(malformed.stdout)
                print(malformed.stderr, file=sys.stderr)
                raise SystemExit(f"{label} comparison missing parse_error")
            if "bad_row_width" not in malformed.stdout:
                print(malformed.stdout)
                raise SystemExit(f"{label} comparison missing bad_row_width detail")

        same_report = run_compare_reports(baseline_report, candidate_report)
        if same_report.returncode != 0:
            print(same_report.stdout)
            print(same_report.stderr, file=sys.stderr)
            raise SystemExit("expected report-based full-lite comparison to pass")
        for phrase in (
            "baseline_report=",
            "candidate_report=",
            "report_output_field=merged_output",
            "full_rows_equal=true",
        ):
            if phrase not in same_report.stdout:
                raise SystemExit(f"report comparison missing phrase: {phrase}")

        topk_report = run_compare_reports(
            baseline_topk_report,
            candidate_topk_report,
            output_field="topk_lite_output",
        )
        if topk_report.returncode != 0:
            print(topk_report.stdout)
            print(topk_report.stderr, file=sys.stderr)
            raise SystemExit("expected explicit topk_lite report comparison to pass")
        if "report_output_field=topk_lite_output" not in topk_report.stdout:
            raise SystemExit("topk report comparison missing output field")

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
