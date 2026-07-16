#!/usr/bin/env python3
"""Reject unsupported universal paper claims outside explicit boundary contexts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    re.compile(r"universally accelerates", re.IGNORECASE),
    re.compile(r"40x faster than LongTarget", re.IGNORECASE),
    re.compile(r"full replacement", re.IGNORECASE),
    re.compile(r"all short queries", re.IGNORECASE),
    re.compile(r"long-query acceleration supported", re.IGNORECASE),
    re.compile(r"GPU traceback authority", re.IGNORECASE),
)
BOUNDARY_MARKERS = (
    "do not", "does not", "not claim", "not a", "forbidden",
    "prohibited", "unsupported wording", "cannot", "no claim",
)


def find_violations(documents: Mapping[str, str]) -> list[str]:
    violations: list[str] = []
    for name in sorted(documents):
        for line_number, line in enumerate(documents[name].splitlines(), start=1):
            lowered = line.lower()
            if any(marker in lowered for marker in BOUNDARY_MARKERS):
                continue
            for pattern in FORBIDDEN:
                if pattern.search(line):
                    violations.append(f"{name}:{line_number}: {pattern.pattern}: {line.strip()}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-dir", type=Path, default=ROOT / "paper")
    args = parser.parse_args()
    documents = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(args.paper_dir.glob("*.md"))
    }
    violations = find_violations(documents)
    if violations:
        for violation in violations:
            print(violation)
        return 1
    print(f"claim_language_files={len(documents)}")
    print("claim_language_audit=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
