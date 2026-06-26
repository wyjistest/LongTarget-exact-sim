#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path


SCHEMA = "FASIM_TFO_ARCHIVE_MANIFEST_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_KEYS = (
    "archive_manifest_schema",
    "archive_path",
    "archive_sha256",
    "archive_magic",
    "archive_version",
    "archive_terminator_present",
    "query_fasta_path",
    "query_fasta_sha256",
    "target_fasta_path",
    "target_fasta_sha256",
    "restored_output_path",
    "restored_sha256",
    "restore_command",
    "restore_rows",
    "archive_bytes",
    "restored_bytes",
)


def _read_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            raise SystemExit(f"malformed manifest line {lineno}: {line}")
        values[parts[0]] = parts[1]
    return values


def _positive_int(value: str) -> bool:
    try:
        return int(value) > 0
    except ValueError:
        return False


def _has_option(tokens: list[str], option: str, expected_value: str) -> bool:
    for index, token in enumerate(tokens):
        if token == option and index + 1 < len(tokens):
            return tokens[index + 1] == expected_value
        if token.startswith(option + "="):
            return token.split("=", 1)[1] == expected_value
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Fasim GASAL2 archive delivery manifest."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    values = _read_manifest(args.manifest)
    missing = [key for key in REQUIRED_KEYS if key not in values]
    restore_tokens = shlex.split(values.get("restore_command", ""))

    archive_sha_valid = bool(SHA256_RE.fullmatch(values.get("archive_sha256", "")))
    query_sha_valid = bool(SHA256_RE.fullmatch(values.get("query_fasta_sha256", "")))
    target_sha_valid = bool(SHA256_RE.fullmatch(values.get("target_fasta_sha256", "")))
    restored_sha_valid = bool(SHA256_RE.fullmatch(values.get("restored_sha256", "")))
    required_paths_present = all(
        values.get(key, "")
        for key in (
            "archive_path",
            "query_fasta_path",
            "target_fasta_path",
            "restored_output_path",
        )
    )
    restore_command_present = bool(values.get("restore_command", ""))
    restore_has_archive = _has_option(
        restore_tokens, "--archive", values.get("archive_path", "")
    )
    restore_has_output = _has_option(
        restore_tokens, "--output", values.get("restored_output_path", "")
    )
    restore_has_query = _has_option(
        restore_tokens, "--query-fasta", values.get("query_fasta_path", "")
    )
    restore_has_target = _has_option(
        restore_tokens, "--target-fasta", values.get("target_fasta_path", "")
    )
    positive_numbers = all(
        _positive_int(values.get(key, ""))
        for key in ("restore_rows", "archive_bytes", "restored_bytes")
    )

    valid = (
        not missing
        and values.get("archive_manifest_schema") == SCHEMA
        and values.get("archive_magic") == "FATFOC1"
        and values.get("archive_version") == "2"
        and values.get("archive_terminator_present") == "1"
        and archive_sha_valid
        and query_sha_valid
        and target_sha_valid
        and restored_sha_valid
        and required_paths_present
        and restore_command_present
        and restore_has_archive
        and restore_has_output
        and restore_has_query
        and restore_has_target
        and positive_numbers
    )

    output = {
        "archive_manifest_schema": values.get("archive_manifest_schema", ""),
        "archive_manifest_valid": "1" if valid else "0",
        "archive_version": values.get("archive_version", ""),
        "archive_terminator_present": values.get("archive_terminator_present", ""),
        "restore_command_present": "1" if restore_command_present else "0",
        "restore_command_has_archive": "1" if restore_has_archive else "0",
        "restore_command_has_output": "1" if restore_has_output else "0",
        "restore_command_has_query_fasta": "1" if restore_has_query else "0",
        "restore_command_has_target_fasta": "1" if restore_has_target else "0",
        "archive_sha256_valid": "1" if archive_sha_valid else "0",
        "query_fasta_sha256_valid": "1" if query_sha_valid else "0",
        "target_fasta_sha256_valid": "1" if target_sha_valid else "0",
        "restored_sha256_valid": "1" if restored_sha_valid else "0",
        "required_paths_present": "1" if required_paths_present else "0",
        "positive_size_and_row_counts": "1" if positive_numbers else "0",
        "missing_required_keys": ",".join(missing) if missing else "none",
        "archive_manifest_decision": "ready" if valid else "invalid",
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
