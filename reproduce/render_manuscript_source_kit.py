#!/usr/bin/env python3
"""Render the claim-centered manuscript source sheet from the frozen ledger."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURE_TABLE = {
    "C1": "Figures 1D and 2; Tables 1 and 2",
    "C2": "Figure 2; Tables 2 and 3",
    "C3": "Figure 2; Table 3",
    "C4": "Figure 3; Tables 2 and 4",
    "C5": "Figure S1; Table 4",
    "C6": "Figure 3; Table 4",
    "C7": "Figure 4; Supplementary operating-envelope table",
}


def read_claims(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if [row["claim_id"] for row in rows] != [f"C{index}" for index in range(1, 8)]:
        raise ValueError("claim ledger must contain ordered C1-C7 rows")
    return rows


def render(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Results Claim Source Sheet",
        "",
        "Generated from `paper/claim_evidence.tsv` under data freeze",
        "`paper-data-v1-dccfd49-20260716`. This is structured source material,",
        "not manuscript prose.",
    ]
    for row in rows:
        claim = row["claim_id"]
        lines.extend(
            [
                "",
                f"## {claim}",
                "",
                f"- claim_id: `{claim}`",
                f"- one-sentence result: {row['allowed_manuscript_wording']}",
                f"- scope: `{row['contract']}`; workloads `{row['workload_ids']}`.",
                f"- n: `{row['current_n']}`; required repeats `{row['required_repeats']}`.",
                f"- point estimate: `{row['current_value']}`.",
                f"- interval or range: `{row['final_interval_or_range']}`.",
                f"- correctness: `{row['correctness_status']}`.",
                f"- figure/table: {FIGURE_TABLE[claim]}.",
                f"- source data: `{row['current_evidence_path']}` filtered by `{row['source_data_filter']}`.",
                f"- allowed wording: {row['allowed_manuscript_wording']}",
                f"- forbidden extrapolation: {row['gap']}",
            ]
        )
    return "\n".join(lines) + "\n"


def atomic_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", type=Path, default=ROOT / "paper/claim_evidence.tsv")
    parser.add_argument("--output", type=Path, default=ROOT / "paper/results_claims.md")
    args = parser.parse_args()
    atomic_text(args.output, render(read_claims(args.claims)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
