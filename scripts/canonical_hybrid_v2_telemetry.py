#!/usr/bin/env python3
"""Validate canonical-hybrid-v2 per-attempt telemetry and output mapping."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/canonical_hybrid_v2_attempt_telemetry.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FIELDS = tuple(SCHEMA["columns"])
SELECTION_REASONS = frozenset(SCHEMA["selection_reason_enum"])
FINAL_STATUSES = frozenset(SCHEMA["final_status_enum"])
SELECTED_REASONS = frozenset(("threshold", "best_fallback", "last"))
EMIT_REASONS = frozenset(("threshold", "best_fallback", "last", "not_emitted", "not_selected"))
INTEGER_FIELDS = frozenset(
    (
        "batch_id",
        "attempt_index",
        "task_id",
        "scoreinfo_index",
        "scoreinfo_position",
        "rule",
        "strand",
        "para",
        "identity_round",
        "start",
        "cutlength",
        "prealign_threshold",
        "gpu_score",
        "gpu_query_end",
        "gpu_ref_end_global",
        "selected",
        "cpu_called",
        "cpu_score",
        "cpu_query_begin",
        "cpu_query_end",
        "cpu_ref_begin_local",
        "cpu_ref_end_local",
    )
)
METRIC_NAMES = (
    "benchmark.fasim_canonical_hybrid_v2_requested",
    "benchmark.fasim_canonical_hybrid_v2_active",
    "benchmark.fasim_canonical_hybrid_v2_telemetry_rows",
    "benchmark.fasim_canonical_hybrid_v2_selected_rows",
    "benchmark.fasim_canonical_hybrid_v2_cpu_traceback_rows",
    "benchmark.fasim_canonical_hybrid_v2_final_row_mappings",
    "benchmark.fasim_gasal2_fallbacks",
    "benchmark.fasim_gasal2_score_selected_attempts",
    "benchmark.fasim_gasal2_cpu_traceback_align_calls",
)
TIMING_NAMES = (
    "benchmark.fasim_gasal2_longtarget_score_select_seconds",
    "benchmark.fasim_gasal2_cpu_traceback_replay_seconds",
    "benchmark.fasim_gasal2_cpu_traceback_align_seconds",
    "benchmark.fasim_gasal2_cpu_traceback_convert_seconds",
    "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds",
    "benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds",
)
CIGAR = re.compile(r"(?:[0-9]+[MIDNSHP=X])+|\*")
DIGEST = re.compile(r"fnv1a64:[0-9a-f]{16}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fnv1a64(text: str) -> str:
    value = 1469598103934665603
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f"fnv1a64:{value:016x}"


def output_row_digests(path: Path) -> list[str]:
    require(path.is_file() and not path.is_symlink(), f"unsafe TFOsorted output: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    require(lines, "empty TFOsorted output")
    expected_header = (
        "QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
        "StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\tStrand\t"
        "Rule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\tTFO sequence\tTTS sequence"
    )
    require(lines[0] == expected_header, "TFOsorted header drift")
    for line in lines[1:]:
        require(len(line.split("\t")) == 19, "malformed TFOsorted data row")
    return [fnv1a64(line) for line in lines[1:]]


def read_telemetry(path: Path) -> list[dict[str, object]]:
    require(path.is_file() and not path.is_symlink(), f"unsafe telemetry path: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == FIELDS, "telemetry TSV schema drift")
        raw_rows = list(reader)
    require(raw_rows, "telemetry contains no attempt rows")
    rows: list[dict[str, object]] = []
    for index, raw in enumerate(raw_rows, 2):
        require(tuple(raw) == FIELDS, f"malformed telemetry row {index}")
        row: dict[str, object] = dict(raw)
        for field in INTEGER_FIELDS:
            try:
                row[field] = int(str(raw[field]))
            except ValueError as exc:
                raise ValueError(f"non-integer {field} at telemetry row {index}") from exc
        require(row["selected"] in (0, 1), f"invalid selected flag at row {index}")
        require(row["cpu_called"] in (0, 1), f"invalid cpu_called flag at row {index}")
        require(row["selection_reason"] in SELECTION_REASONS, f"invalid selection reason at row {index}")
        require(row["cpu_emit_reason"] in EMIT_REASONS, f"invalid CPU emit reason at row {index}")
        require(row["final_status"] in FINAL_STATUSES, f"invalid final status at row {index}")
        require(6 <= int(row["identity_round"]) <= 10, f"invalid identity round at row {index}")
        require(int(row["cutlength"]) > 0, f"invalid cutlength at row {index}")
        selected = bool(row["selected"])
        cpu_called = bool(row["cpu_called"])
        require(selected == (row["selection_reason"] in SELECTED_REASONS), f"selection reason disagreement at row {index}")
        require(selected == cpu_called, f"selected attempt lacks exactly one CPU traceback at row {index}")
        if cpu_called:
            require(CIGAR.fullmatch(str(row["cpu_cigar"])) is not None, f"invalid CPU CIGAR at row {index}")
            require(int(row["cpu_score"]) >= 0, f"negative CPU score at row {index}")
            require(row["cpu_emit_reason"] != "not_selected", f"selected attempt lacks CPU emit decision at row {index}")
            if int(row["cpu_score"]) > 0:
                require(int(row["cpu_query_begin"]) >= 0, f"invalid CPU query begin at row {index}")
                require(int(row["cpu_query_end"]) >= int(row["cpu_query_begin"]), f"invalid CPU query interval at row {index}")
                require(int(row["cpu_ref_begin_local"]) >= 0, f"invalid CPU reference begin at row {index}")
                require(int(row["cpu_ref_end_local"]) >= int(row["cpu_ref_begin_local"]), f"invalid CPU reference interval at row {index}")
            else:
                require(row["cpu_emit_reason"] == "not_emitted", f"zero-score CPU alignment was emitted at row {index}")
        else:
            require(row["cpu_cigar"] == "NA", f"unselected attempt has CPU CIGAR at row {index}")
            require(row["cpu_emit_reason"] == "not_selected", f"unselected attempt has emit reason at row {index}")
            require(row["final_status"] == "not_selected", f"unselected attempt has final state at row {index}")
        converted = str(row["converted_row_digest"])
        final = str(row["final_row_digest"])
        require(converted == "NA" or DIGEST.fullmatch(converted) is not None, f"invalid converted digest at row {index}")
        require(final == "NA" or DIGEST.fullmatch(final) is not None, f"invalid final digest at row {index}")
        if selected and row["cpu_emit_reason"] == "not_emitted":
            require(converted == "NA" and final == "NA", f"non-emitted attempt has a row digest at row {index}")
            require(row["final_status"] == "cpu_not_emitted", f"non-emitted attempt status drift at row {index}")
        if converted == "NA" and selected and row["cpu_emit_reason"] != "not_emitted":
            require(row["final_status"] == "emitted_not_converted", f"unconverted attempt status drift at row {index}")
        if converted != "NA" and final == "NA":
            require(row["final_status"] == "converted_not_final", f"filtered row status drift at row {index}")
        if final != "NA":
            require(final == converted, f"final/converted digest disagreement at row {index}")
            require(row["final_status"] == "final_row", f"mapped final digest lacks final status at row {index}")
        rows.append(row)

    by_batch: dict[int, list[int]] = defaultdict(list)
    identities: set[tuple[int, int]] = set()
    for row in rows:
        identity = (int(row["batch_id"]), int(row["attempt_index"]))
        require(identity not in identities, "duplicate batch/attempt telemetry identity")
        identities.add(identity)
        by_batch[identity[0]].append(identity[1])
    for batch_id, indexes in by_batch.items():
        require(sorted(indexes) == list(range(len(indexes))), f"non-contiguous attempt indexes in batch {batch_id}")
    require(sorted(by_batch) == list(range(len(by_batch))), "non-contiguous telemetry batch IDs")
    return rows


def parse_metrics(stderr: str) -> dict[str, object]:
    wanted = set(METRIC_NAMES) | set(TIMING_NAMES)
    values: dict[str, object] = {}
    for line in stderr.splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name not in wanted:
            continue
        require(name not in values, f"duplicate runtime metric: {name}")
        try:
            values[name] = float(value) if name in TIMING_NAMES else int(value)
        except ValueError as exc:
            raise ValueError(f"invalid runtime metric: {name}={value}") from exc
    missing = sorted(wanted - set(values))
    require(not missing, f"missing runtime metrics: {', '.join(missing)}")
    return values


def validate_attempt(
    telemetry_path: Path,
    output_path: Path,
    stderr: str,
) -> dict[str, object]:
    rows = read_telemetry(telemetry_path)
    metrics = parse_metrics(stderr)
    output_digests = output_row_digests(output_path)
    mapped_digests = {
        str(row["final_row_digest"])
        for row in rows
        if row["final_row_digest"] != "NA"
    }
    require(mapped_digests == set(output_digests), "telemetry final-row digest set does not equal TFOsorted output")
    selected = sum(int(row["selected"]) for row in rows)
    cpu_called = sum(int(row["cpu_called"]) for row in rows)
    final_mappings = sum(row["final_row_digest"] != "NA" for row in rows)
    expected = {
        "benchmark.fasim_canonical_hybrid_v2_requested": 1,
        "benchmark.fasim_canonical_hybrid_v2_active": 1,
        "benchmark.fasim_canonical_hybrid_v2_telemetry_rows": len(rows),
        "benchmark.fasim_canonical_hybrid_v2_selected_rows": selected,
        "benchmark.fasim_canonical_hybrid_v2_cpu_traceback_rows": cpu_called,
        "benchmark.fasim_canonical_hybrid_v2_final_row_mappings": final_mappings,
        "benchmark.fasim_gasal2_fallbacks": 0,
        "benchmark.fasim_gasal2_score_selected_attempts": selected,
        "benchmark.fasim_gasal2_cpu_traceback_align_calls": cpu_called,
    }
    for name, value in expected.items():
        require(metrics[name] == value, f"runtime/telemetry count disagreement: {name}")
    timings = {name.removeprefix("benchmark."): metrics[name] for name in TIMING_NAMES}
    require(all(float(value) >= 0 for value in timings.values()), "negative component timing")
    return {
        "attempt_rows": len(rows),
        "batch_count": len({int(row["batch_id"]) for row in rows}),
        "selected_attempts": selected,
        "cpu_traceback_calls": cpu_called,
        "selection_reasons": dict(sorted(Counter(str(row["selection_reason"]) for row in rows).items())),
        "cpu_emit_reasons": dict(sorted(Counter(str(row["cpu_emit_reason"]) for row in rows).items())),
        "final_statuses": dict(sorted(Counter(str(row["final_status"]) for row in rows).items())),
        "final_row_mappings": final_mappings,
        "output_rows": len(output_digests),
        "output_row_digest_set": sorted(set(output_digests)),
        "output_row_digest_counts": dict(sorted(Counter(output_digests).items())),
        "fallbacks": int(metrics["benchmark.fasim_gasal2_fallbacks"]),
        "component_timings": timings,
    }


def telemetry_tsv_bytes(rows: Iterable[dict[str, object]]) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")
