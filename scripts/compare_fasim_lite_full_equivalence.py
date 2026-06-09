#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


LITE_COLUMNS = [
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

TFOSORTED_COLUMNS = [
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

SUPPORTED_SCHEMAS = {
    "lite": LITE_COLUMNS,
    "tfosorted": TFOSORTED_COLUMNS,
}


class SchemaError(RuntimeError):
    pass


class ParseError(RuntimeError):
    pass


class ReportError(RuntimeError):
    pass


def _format_columns(columns: list[str]) -> str:
    return ",".join(columns) if columns else "none"


def _schema_name(header: list[str]) -> str | None:
    for name, columns in SUPPORTED_SCHEMAS.items():
        if header == columns:
            return name
    return None


def _check_row_width(
    path: Path, row_number: int, row: dict[str, str], columns: list[str]
) -> None:
    if None in row:
        raise ParseError(
            f"path={path} row={row_number} bad_row_width=too_many_fields"
        )
    missing_values = [column for column in columns if row.get(column) is None]
    if missing_values:
        raise ParseError(
            f"path={path} row={row_number} bad_row_width=too_few_fields "
            f"missing_values={_format_columns(missing_values)}"
        )


def _read_rows(path: Path) -> tuple[str, list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = reader.fieldnames or []
        schema = _schema_name(header)
        if schema is None:
            canonical = sorted(set().union(*SUPPORTED_SCHEMAS.values()))
            missing = [column for column in canonical if column not in header]
            extra = [column for column in header if column not in canonical]
            raise SchemaError(
                f"path={path} unsupported_schema header_columns={_format_columns(header)} "
                f"missing_known_columns={_format_columns(missing)} "
                f"extra_columns={_format_columns(extra)}"
            )
        columns = SUPPORTED_SCHEMAS[schema]
        rows = []
        for row_number, row in enumerate(reader, 2):
            _check_row_width(path, row_number, row, columns)
            rows.append(row)
        return schema, columns, rows


def _row_key(row: dict[str, str], columns: list[str]) -> str:
    return "\t".join(row.get(column, "") for column in columns)


def _canonical_keys(rows: list[dict[str, str]], columns: list[str]) -> list[str]:
    return sorted({_row_key(row, columns) for row in rows})


def _digest(keys: list[str]) -> str:
    return hashlib.sha256(("\n".join(keys) + "\n").encode("utf-8")).hexdigest()


def _print_optional_row(label: str, rows: set[str]) -> None:
    if rows:
        print(f"{label}={sorted(rows)[0]}")
    else:
        print(f"{label}=none")


def _load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReportError(f"path={path} error=not_json_object")
    return payload


def _resolve_report_output(report_path: Path, output_field: str) -> Path:
    payload = _load_report(report_path)
    raw_output = payload.get(output_field)
    if not isinstance(raw_output, str) or not raw_output:
        raise ReportError(f"path={report_path} missing_output_field={output_field}")
    output = Path(raw_output)
    if not output.is_absolute():
        output = report_path.parent / output
    if not output.exists():
        raise ReportError(
            f"path={report_path} output_field={output_field} output_missing={output}"
        )
    return output


def _resolve_input_path(
    *,
    direct_path: Path | None,
    report_path: Path | None,
    output_field: str,
    label: str,
) -> tuple[Path, Path | None]:
    if (direct_path is None) == (report_path is None):
        raise ReportError(
            f"{label}=requires_exactly_one_of_direct_path_or_report_path"
        )
    if report_path is None:
        assert direct_path is not None
        return direct_path, None
    return _resolve_report_output(report_path, output_field), report_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare full canonical Fasim lite/TFO row sets."
    )
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--candidate-report", type=Path)
    parser.add_argument("--report-output-field", default="merged_output")
    args = parser.parse_args()

    try:
        baseline_path, baseline_report = _resolve_input_path(
            direct_path=args.baseline,
            report_path=args.baseline_report,
            output_field=args.report_output_field,
            label="baseline",
        )
        candidate_path, candidate_report = _resolve_input_path(
            direct_path=args.candidate,
            report_path=args.candidate_report,
            output_field=args.report_output_field,
            label="candidate",
        )
    except (json.JSONDecodeError, OSError, ReportError) as exc:
        print(f"report_error={exc}")
        return 2

    try:
        baseline_schema, baseline_columns, baseline_rows = _read_rows(baseline_path)
        candidate_schema, candidate_columns, candidate_rows = _read_rows(candidate_path)
    except SchemaError as exc:
        print(f"schema_error={exc}")
        return 2
    except ParseError as exc:
        print(f"parse_error={exc}")
        return 2
    if baseline_schema != candidate_schema:
        print(
            "schema_error="
            f"baseline_schema={baseline_schema} candidate_schema={candidate_schema} "
            "schemas_must_match=true"
        )
        return 2
    baseline_keys = _canonical_keys(baseline_rows, baseline_columns)
    candidate_keys = _canonical_keys(candidate_rows, candidate_columns)
    baseline_set = set(baseline_keys)
    candidate_set = set(candidate_keys)
    missing = baseline_set - candidate_set
    extra = candidate_set - baseline_set
    equal = not missing and not extra

    if baseline_report is not None:
        print(f"baseline_report={baseline_report}")
    if candidate_report is not None:
        print(f"candidate_report={candidate_report}")
    if baseline_report is not None or candidate_report is not None:
        print(f"report_output_field={args.report_output_field}")
    print(f"baseline={baseline_path}")
    print(f"candidate={candidate_path}")
    print(f"schema={baseline_schema}")
    print(f"baseline_rows={len(baseline_rows)}")
    print(f"candidate_rows={len(candidate_rows)}")
    print(f"baseline_unique_rows={len(baseline_keys)}")
    print(f"candidate_unique_rows={len(candidate_keys)}")
    print(f"baseline_full_digest={_digest(baseline_keys)}")
    print(f"candidate_full_digest={_digest(candidate_keys)}")
    print(f"missing_rows={len(missing)}")
    print(f"extra_rows={len(extra)}")
    _print_optional_row("first_missing_row", missing)
    _print_optional_row("first_extra_row", extra)
    print(f"full_rows_equal={str(equal).lower()}")
    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
