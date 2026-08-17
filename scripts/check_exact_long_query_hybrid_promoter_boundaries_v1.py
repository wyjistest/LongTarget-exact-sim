#!/usr/bin/env python3
"""Exercise positive boundary controls on the frozen production promoter target."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from exact_long_query_promoter_mapping import PromoterMapping, read_single_fasta


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMOTER_ROOT = Path(
    "/data/wenyujianData/linjieData/promoter_sequences/"
    "human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1"
)


class BoundaryError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BoundaryError(message)


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run(promoter_root: Path) -> dict[str, object]:
    mapping = PromoterMapping(promoter_root)
    context = mapping.target_context("logical_full_concat")
    _, target = read_single_fasta(context.path)
    fixtures: list[dict[str, object]] = []

    edge_component = next(component for component in context.components if component.n_count == 0)
    for label, start, end in (
        ("component_left_edge", edge_component.logical_start0, edge_component.logical_start0 + 1),
        ("component_right_edge", edge_component.logical_end0 - 1, edge_component.logical_end0),
    ):
        reason, associations = mapping.map_interval(context, target, start, end)
        require(reason is None and associations, f"{label} did not map")
        fixtures.append({"fixture": label, "status": "pass", "component_id": edge_component.component_id, "associations": len(associations)})

    left, right = context.components[0], context.components[1]
    require(left.logical_end0 == right.logical_start0, "positive cross-component fixture is not adjacent")
    reason, associations = mapping.map_interval(
        context, target, left.logical_end0 - 1, right.logical_start0 + 1
    )
    require(reason == "cross_component_boundary" and not associations, "cross-component hit was not rejected")
    fixtures.append({
        "fixture": "cross_component_positive_control",
        "status": "pass",
        "left_component_id": left.component_id,
        "right_component_id": right.component_id,
        "reason": reason,
    })

    n_position = target.index("N")
    reason, associations = mapping.map_interval(context, target, n_position, n_position + 1)
    require(reason == "overlaps_reference_N" and not associations, "reference-N hit was not rejected")
    fixtures.append({
        "fixture": "reference_n_positive_control",
        "status": "pass",
        "logical_position0": n_position,
        "reason": reason,
    })

    overlap_fixture = None
    for component in context.components:
        promoters = mapping.memberships[component.component_id]
        if len(promoters) < 2 or component.n_count:
            continue
        overlap_start = max(promoter.genomic_start0 for promoter in promoters)
        overlap_end = min(promoter.genomic_end0 for promoter in promoters)
        if overlap_start < overlap_end:
            local_start = component.logical_start0 + overlap_start - component.genomic_start0
            reason, associations = mapping.map_interval(context, target, local_start, local_start + 1)
            if reason is None and len(associations) >= 2:
                overlap_fixture = (component, local_start, associations)
                break
    require(overlap_fixture is not None, "no overlapping-promoter positive control found")
    component, local_start, associations = overlap_fixture
    fixtures.append({
        "fixture": "overlapping_promoter_membership",
        "status": "pass",
        "component_id": component.component_id,
        "logical_position0": local_start,
        "promoter_ids": [row["promoter_id"] for row in associations],
    })

    for strand in ("+", "-"):
        selected = None
        for component in context.components:
            if component.n_count:
                continue
            for promoter in mapping.memberships[component.component_id]:
                if promoter.gene_strand != strand:
                    continue
                genomic_start = promoter.tss1 - 1
                logical_start = component.logical_start0 + genomic_start - component.genomic_start0
                reason, associations = mapping.map_interval(context, target, logical_start, logical_start + 1)
                matching = [row for row in associations if row["promoter_id"] == promoter.promoter_id]
                if reason is None and matching:
                    selected = (component, promoter, matching[0])
                    break
            if selected:
                break
        require(selected is not None, f"no {strand} promoter coordinate fixture found")
        component, promoter, association = selected
        require(
            association["relative_to_tss_transcriptional_start"] == 0
            and association["relative_to_tss_transcriptional_end"] == 0,
            f"{strand} TSS-relative coordinate mismatch",
        )
        fixtures.append({
            "fixture": "plus_tss_relative_coordinate" if strand == "+" else "minus_tss_relative_coordinate",
            "status": "pass",
            "component_id": component.component_id,
            "promoter_id": promoter.promoter_id,
            "relative_start": 0,
            "relative_end": 0,
        })

    return {
        "schema_version": "exact_long_query_hybrid_promoter_boundary_receipt_v1",
        "status": "boundary_fixture_gate_pass",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "promoter_root": str(promoter_root),
        "target_file_sha256": context.file_sha256,
        "target_length_bp": context.length_bp,
        "reference_n_count": target.count("N"),
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "positive_cross_component_control_exercised": True,
        "positive_reference_n_control_exercised": True,
        "mapper_sha256": hashlib.sha256((ROOT / "scripts/exact_long_query_promoter_mapping.py").read_bytes()).hexdigest(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--promoter-root", type=Path, default=DEFAULT_PROMOTER_ROOT)
    result.add_argument("--output", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    require(not args.output.exists(), f"refusing to overwrite boundary receipt: {args.output}")
    value = run(args.promoter_root)
    atomic_json(args.output, value)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BoundaryError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(2)
