#!/usr/bin/env python3
"""Finalize deterministic successor Phase 6 resources, tables, and figure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/experimental-phase6"
ATTEMPT_PLAN = PAPER / "experimental_attempt_plan.tsv"
METRICS = PAPER / "source_data/experimental_metrics.tsv"
FAILURES = PAPER / "source_data/experimental_failure_ledger.tsv"
BOOTSTRAP = PAPER / "source_data/experimental_bootstrap.tsv"
REGION_SCORES = PAPER / "source_data/experimental_region_scores.tsv"
RECEIPT = PAPER / "biological_utility_receipt.json"
DECISION = PAPER / "biological_utility_decision.json"
RESOURCES = PAPER / "biological_utility_actual_resources.json"
EXTERNAL = PAPER / "biological_utility_external_diagnostics.tsv"
TABLE = PAPER / "tables/biological_utility.tsv"
FIGURE = PAPER / "figures/biological_utility.svg"
ARTIFACT_MANIFEST = PAPER / "biological_utility_artifact_manifest.tsv"
FIXED_TOTAL_BYTES = 64 * 1024**3
TRACKED_RESERVATION_BYTES = 256 * 1024**2


class FinalizeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FinalizeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    require(fields and all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return fields, rows


def tsv_bytes(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in fields})
    return output.getvalue().encode("utf-8")


def directory_file_bytes(path: Path) -> int:
    require(path.is_dir() and not path.is_symlink(), f"missing or unsafe artifact root: {path}")
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp lacks timezone")
    return parsed


def resource_value(attempts: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    summary = read_json(ARTIFACT_ROOT / "run-summary.json")
    snapshot = read_json(ARTIFACT_ROOT / "execution-snapshot.json")
    decision = read_json(DECISION)
    receipts = [read_json(ROOT / row["artifact_root"] / "attempt-complete.json") for row in attempts]
    require(summary["status"] == "complete" and summary["terminal_attempt_count"] == 15, "Phase 6 run is not terminal")
    require(len(receipts) == 15 and sum(receipt["status"] == "success" for receipt in receipts) == 10, "Phase 6 receipt count drift")
    require(decision["decision"] == "no_go" and decision["primary_technical_failure_count"] == 0, "Phase 6 scientific decision drift")
    predecessor_bytes = directory_file_bytes(ROOT / ".paper-artifacts/biological-topk")
    successor_bytes = directory_file_bytes(ROOT / ".paper-artifacts/biological-topk-successor")
    formal_bytes = predecessor_bytes + successor_bytes
    total_with_reservation = formal_bytes + TRACKED_RESERVATION_BYTES
    started = parse_utc(snapshot["created_utc"])
    completed = parse_utc(summary["updated_utc"])
    elapsed = (completed - started).total_seconds()
    require(elapsed >= 0, "Phase 6 elapsed time is negative")
    gpu_seconds = float(summary["gpu_wall_seconds"])
    cpu_seconds = float(summary["cpu_wall_seconds"])
    return {
        "schema_version": 1,
        "phase": 6,
        "status": "pass_fixed_budget",
        "scientific_decision": decision["decision"],
        "planned_attempt_count": 15,
        "terminal_attempt_count": len(receipts),
        "successful_primary_attempt_count": sum(receipt["status"] == "success" and receipt["arm"] in {"A", "G"} for receipt in receipts),
        "primary_technical_failure_count": sum(receipt["status"] != "success" and receipt["arm"] in {"A", "G"} for receipt in receipts),
        "external_technical_failure_count": sum(receipt["status"] != "success" and receipt["arm"] == "X" for receipt in receipts),
        "gpu_backend_wall_seconds": format(gpu_seconds, ".9f"),
        "gpu_backend_hours": format(gpu_seconds / 3600, ".17g"),
        "cpu_and_external_backend_wall_seconds": format(cpu_seconds, ".9f"),
        "cpu_and_external_backend_wall_hours": format(cpu_seconds / 3600, ".17g"),
        "scheduled_epoch_elapsed_wall_seconds": format(elapsed, ".6f"),
        "max_gpu_hours": 96,
        "max_cpu_wall_hours": 96,
        "max_infrastructure_repair_epochs": 1,
        "infrastructure_repair_epochs_used": 0,
        "predecessor_retained_artifact_bytes": predecessor_bytes,
        "successor_artifact_bytes_through_phase6_runtime": successor_bytes,
        "formal_artifact_bytes": formal_bytes,
        "tracked_evidence_reservation_bytes": TRACKED_RESERVATION_BYTES,
        "actual_total_artifact_storage_bytes_with_tracked_reservation": total_with_reservation,
        "fixed_total_artifact_storage_bytes": FIXED_TOTAL_BYTES,
        "artifact_storage_margin_bytes": FIXED_TOTAL_BYTES - total_with_reservation,
        "gpu_budget_gate_pass": gpu_seconds <= 96 * 3600,
        "cpu_wall_budget_gate_pass": cpu_seconds <= 96 * 3600,
        "fixed_artifact_budget_gate_pass": total_with_reservation <= FIXED_TOTAL_BYTES,
        "all_fixed_budget_gates_pass": gpu_seconds <= 96 * 3600 and cpu_seconds <= 96 * 3600 and total_with_reservation <= FIXED_TOTAL_BYTES,
        "run_summary_sha256": sha256_file(ARTIFACT_ROOT / "run-summary.json"),
        "execution_snapshot_sha256": sha256_file(ARTIFACT_ROOT / "execution-snapshot.json"),
        "resource_values_are_performance_claims": False,
    }


EXTERNAL_FIELDS = (
    "dataset_id",
    "outer_lncRNA_id",
    "attempt_id",
    "terminal_status",
    "returncode",
    "timed_out",
    "wall_seconds",
    "output_available",
    "failure_reason",
    "primary_metric_comparable",
    "used_in_primary_inference",
)


def external_rows(attempts: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for attempt in attempts:
        if attempt["arm"] != "X":
            continue
        receipt = read_json(ROOT / attempt["artifact_root"] / "attempt-complete.json")
        rows.append(
            {
                "dataset_id": attempt["dataset_id"],
                "outer_lncRNA_id": attempt["outer_lncRNA_id"],
                "attempt_id": attempt["attempt_id"],
                "terminal_status": receipt["status"],
                "returncode": receipt["execution"]["returncode"],
                "timed_out": int(receipt["execution"]["timed_out"]),
                "wall_seconds": receipt["execution"]["wall_seconds"],
                "output_available": int(receipt["output_sha256"] is not None),
                "failure_reason": receipt["failure_reason"] or "NA",
                "primary_metric_comparable": 0,
                "used_in_primary_inference": 0,
            }
        )
    require(len(rows) == 5, "external diagnostic attempt count drift")
    return rows


TABLE_FIELDS = (
    "dataset_id",
    "outer_lncRNA_id",
    "A_AUCPR",
    "G_AUCPR",
    "G_minus_A_AUCPR",
    "A_recall_at_P",
    "G_recall_at_P",
    "G_minus_A_recall_at_P",
    "prevalence",
    "G_precision_at_P",
    "G_fold_enrichment",
    "G_log_enrichment",
    "G_zero_precision",
)


def table_rows(metrics: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    by_key = {(row["dataset_id"], row["arm"]): row for row in metrics}
    datasets = sorted({row["dataset_id"] for row in metrics})
    rows = []
    for dataset_id in datasets:
        a, g = by_key[(dataset_id, "A")], by_key[(dataset_id, "G")]
        rows.append(
            {
                "dataset_id": dataset_id,
                "outer_lncRNA_id": g["outer_lncRNA_id"],
                "A_AUCPR": a["aucpr"],
                "G_AUCPR": g["aucpr"],
                "G_minus_A_AUCPR": format(float(g["aucpr"]) - float(a["aucpr"]), ".17g"),
                "A_recall_at_P": a["recall_at_P"],
                "G_recall_at_P": g["recall_at_P"],
                "G_minus_A_recall_at_P": format(float(g["recall_at_P"]) - float(a["recall_at_P"]), ".17g"),
                "prevalence": g["prevalence"],
                "G_precision_at_P": g["precision_at_P"],
                "G_fold_enrichment": g["fold_enrichment"],
                "G_log_enrichment": g["log_enrichment"],
                "G_zero_precision": g["zero_precision"],
            }
        )
    require(len(rows) == 5, "biological utility table dataset count drift")
    return rows


def figure_bytes(rows: Sequence[Mapping[str, Any]], decision: Mapping[str, Any]) -> bytes:
    width, height = 960, 520
    left, top, chart_width, chart_height = 90, 80, 790, 300
    maximum = 0.16
    labels = {
        "bte_hotair_gse31332": "HOTAIR",
        "bte_hottip_gse114981": "HOTTIP",
        "bte_linc01116_gse227804": "LINC01116",
        "bte_pcgem1_gse47804": "PCGEM1",
        "bte_sra_gse58641": "SRA",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="960" height="520" fill="#ffffff"/>',
        '<text x="90" y="36" font-family="sans-serif" font-size="22" fill="#171717">Independent biological utility by lncRNA</text>',
        '<text x="90" y="60" font-family="sans-serif" font-size="13" fill="#525252">AUCPR versus prevalence; Phase 6 intersection-union decision</text>',
    ]
    for tick in range(5):
        value = tick * 0.04
        y = top + chart_height - value / maximum * chart_height
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_width}" y2="{y:.2f}" stroke="#e5e5e5" stroke-width="1"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" font-size="11" fill="#525252">{value:.2f}</text>')
    group_width = chart_width / len(rows)
    for index, row in enumerate(rows):
        center = left + group_width * (index + 0.5)
        for offset, field, color in ((-25, "A_AUCPR", "#737373"), (0, "G_AUCPR", "#15803d"), (25, "prevalence", "#b91c1c")):
            value = float(row[field])
            bar_height = value / maximum * chart_height
            x = center + offset - 10
            y = top + chart_height - bar_height
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="20" height="{bar_height:.2f}" fill="{color}"/>')
        label = html.escape(labels[str(row["dataset_id"])])
        parts.append(f'<text x="{center:.2f}" y="{top + chart_height + 24}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#262626">{label}</text>')
    parts.extend(
        [
            '<rect x="90" y="440" width="12" height="12" fill="#737373"/><text x="110" y="451" font-family="sans-serif" font-size="12" fill="#262626">CPU AUCPR</text>',
            '<rect x="210" y="440" width="12" height="12" fill="#15803d"/><text x="230" y="451" font-family="sans-serif" font-size="12" fill="#262626">GPU AUCPR</text>',
            '<rect x="330" y="440" width="12" height="12" fill="#b91c1c"/><text x="350" y="451" font-family="sans-serif" font-size="12" fill="#262626">Prevalence</text>',
            f'<text x="90" y="490" font-family="sans-serif" font-size="13" fill="#171717">E1 pass | E2 pass | E3 pass | E4 fail (LCB {html.escape(str(decision["one_sided_95_lcb"]["E4"]))}) | overall no-go</text>',
            '</svg>',
        ]
    )
    return ("\n".join(parts) + "\n").encode("ascii")


MANIFEST_FIELDS = ("path", "size_bytes", "sha256", "evidence_role")


def build() -> dict[Path, bytes]:
    _, attempts = read_tsv(ATTEMPT_PLAN)
    _, metrics = read_tsv(METRICS)
    decision = read_json(DECISION)
    require(len(attempts) == 15 and len(metrics) == 10, "Phase 6 input count drift")
    require(decision["decision"] == "no_go" and decision["endpoint_pass"] == {"E1": True, "E2": True, "E3": True, "E4": False}, "Phase 6 endpoint decision drift")
    generated: dict[Path, bytes] = {
        RESOURCES: canonical_json_bytes(resource_value(attempts)),
        EXTERNAL: tsv_bytes(EXTERNAL_FIELDS, external_rows(attempts)),
    }
    summary_rows = table_rows(metrics)
    generated[TABLE] = tsv_bytes(TABLE_FIELDS, summary_rows)
    generated[FIGURE] = figure_bytes(summary_rows, decision)
    evidence_paths = (
        DECISION,
        RECEIPT,
        REGION_SCORES,
        METRICS,
        FAILURES,
        BOOTSTRAP,
        RESOURCES,
        EXTERNAL,
        TABLE,
        FIGURE,
    )
    manifest_rows = []
    for path in sorted(evidence_paths, key=lambda value: value.as_posix()):
        payload = generated[path] if path in generated else path.read_bytes()
        manifest_rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "evidence_role": "phase6_primary" if path in {DECISION, RECEIPT, REGION_SCORES, METRICS, BOOTSTRAP} else "phase6_supporting",
            }
        )
    generated[ARTIFACT_MANIFEST] = tsv_bytes(MANIFEST_FIELDS, manifest_rows)
    return generated


def write_payloads(payloads: Mapping[Path, bytes]) -> None:
    for path, payload in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payloads = build()
        if args.write:
            write_payloads(payloads)
            print(f"wrote {len(payloads)} successor Phase 6 final artifacts")
            return 0
        stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.is_symlink() or path.read_bytes() != payload]
        require(not stale, f"Phase 6 final artifacts do not reproduce: {stale}")
        print("successor Phase 6 final artifacts reproduce byte-for-byte")
        return 0
    except (FinalizeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"successor Phase 6 finalization failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
