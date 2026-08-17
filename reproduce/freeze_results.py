#!/usr/bin/env python3
"""Freeze derived GASAL2 paper source data with deterministic provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
RUNTIME_EPOCH = 0
DEFAULT_FREEZE_ID = "paper-data-v1-dccfd49-20260716"
COLLECTOR_PARENT_COMMIT = "dccfd49"
ANALYSIS_SEED = 20260715
BOOTSTRAP_RESAMPLES = 10000
SOURCE_FILES = (
    "benchmark_runs.tsv",
    "paired_speedups.tsv",
    "correctness.tsv",
    "generalization.tsv",
    "ablation.tsv",
    "resources.tsv",
    "archive_first.tsv",
    "operating_envelope.tsv",
    "exclusions.tsv",
    "paired_speedup_summary.tsv",
    "paired_speedup_summary.json",
)
MANIFEST_FIELDS = (
    "data_freeze_id",
    "path",
    "kind",
    "row_count",
    "size_bytes",
    "sha256",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        return list(reader)


def validate_freeze_id(path: Path, expected: str) -> int:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        workloads = payload.get("workloads", []) if isinstance(payload, dict) else []
        if not isinstance(workloads, list):
            raise ValueError(f"invalid workload summary JSON: {path}")
        observed = {
            str(row.get("data_freeze_id"))
            for row in workloads
            if isinstance(row, dict)
        }
        row_count = len(workloads)
    else:
        rows = read_tsv(path)
        observed = {row.get("data_freeze_id", "") for row in rows}
        row_count = len(rows)
    if observed != {expected}:
        raise ValueError(
            f"data freeze ID mismatch in {path.name}: expected {expected}, observed {sorted(observed)}"
        )
    return row_count


def build_source_manifest(source_dir: Path, data_freeze_id: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for relative in SOURCE_FILES:
        path = source_dir / relative
        if not path.is_file():
            continue
        rows.append(
            {
                "data_freeze_id": data_freeze_id,
                "path": relative,
                "kind": path.suffix.removeprefix("."),
                "row_count": validate_freeze_id(path, data_freeze_id),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    if not rows:
        raise ValueError(f"no final source-data files found in {source_dir}")
    return rows


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def write_manifest(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def render_freeze_document(
    *,
    data_freeze_id: str,
    manifest_rows: list[dict[str, object]],
    workload_manifest_sha256: str,
    artifact_manifest_sha256: dict[str, str],
    collector_sha256: str,
    analyzer_sha256: str,
    collector_parent_commit: str,
    analysis_seed: int,
    bootstrap_resamples: int,
) -> str:
    artifact_lines = "\n".join(
        f"- `{phase}`: `{digest}`"
        for phase, digest in sorted(artifact_manifest_sha256.items())
    )
    source_lines = "\n".join(
        f"- `{row['path']}`: `{row['sha256']}` ({row['row_count']} rows, {row['size_bytes']} bytes)"
        for row in manifest_rows
    )
    return f"""# GASAL2-LongTarget Paper Data Freeze

```text
data_freeze_id = {data_freeze_id}
paper_runtime_epoch = {RUNTIME_EPOCH}
paper_runtime_commit = {RUNTIME_COMMIT}
collector_parent_commit = {collector_parent_commit}
analysis_seed = {analysis_seed}
bootstrap_resamples = {bootstrap_resamples}
```

This freeze contains derived source data reconstructed from immutable Phase 2-4
receipts, comparator summaries, and manifests. The source-data manifest does not
hash itself or this document; each listed data file is hashed directly.

## Provenance

- Workload manifest SHA-256: `{workload_manifest_sha256}`
- Collector SHA-256: `{collector_sha256}`
- Analyzer SHA-256: `{analyzer_sha256}`

Artifact manifest SHA-256 values:

{artifact_lines}

## Frozen Files

{source_lines}

## Statistical Contract

- Paired speedup is recomputed as baseline wall time divided by candidate wall time.
- Summaries report median, inclusive IQR, and observed range.
- Median bootstrap 95% intervals use seed `{analysis_seed}` and `{bootstrap_resamples}` resamples.
- Workloads with fewer than three pairs have no bootstrap interval.
- Mismatch rows remain included and are not treated as technical exclusions.

## Known Limitations

- The primary hardware evidence is from one GPU generation.
- Fast top-K equivalence is not full-output row-set equivalence.
- Three preregistered supported-query workloads retain clustered TFO1-5 mismatches.
- Full-output workloads are near parity rather than a broad acceleration result.
- KCNQ1OT1 long-query evidence is bounded to max8 dual-grid execution.
- Full KCNQ1OT1 transcript coverage was not run.
- Full hg38 was not run.
- High-density multi-worker configurations on 24 GB GPUs retain OOM evidence; one worker per GPU is the supported density.
- Raw benchmark artifacts remain external under `.paper-artifacts/` and are not tracked in Git.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT / "paper/source_data")
    parser.add_argument("--data-freeze-id", default=DEFAULT_FREEZE_ID)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    rows = build_source_manifest(source_dir, args.data_freeze_id)
    artifact_digests = {
        phase: sha256(ROOT / f"paper/{phase}_artifact_manifest.tsv")
        for phase in ("phase2", "phase3", "phase4")
    }
    write_manifest(source_dir / "source_data_manifest.tsv", rows)
    document = render_freeze_document(
        data_freeze_id=args.data_freeze_id,
        manifest_rows=rows,
        workload_manifest_sha256=sha256(ROOT / "paper/workload_manifest.tsv"),
        artifact_manifest_sha256=artifact_digests,
        collector_sha256=sha256(ROOT / "reproduce/collect_results.py"),
        analyzer_sha256=sha256(ROOT / "reproduce/analyze_results.py"),
        collector_parent_commit=COLLECTOR_PARENT_COMMIT,
        analysis_seed=ANALYSIS_SEED,
        bootstrap_resamples=BOOTSTRAP_RESAMPLES,
    )
    atomic_write(source_dir / "DATA_FREEZE.md", document)
    print(f"data_freeze_id={args.data_freeze_id}")
    print(f"frozen_source_files={len(rows)}")
    print(f"runtime_commit={RUNTIME_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
