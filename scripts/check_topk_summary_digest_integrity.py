#!/usr/bin/env python3
"""Verify topk_summary.tsv digests recorded by the sharded runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CANONICAL_SORT_COLUMNS = (
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
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
)
TOPK_MODES = ("score", "stability", "nt_score")
FORMAL_GASAL2_MAX_QUERY_LEN = 2812
FORMAL_GASAL2_MAX_BATCH = 30000
FORMAL_GASAL2_MAX_STREAMS = 16
FORMAL_GASAL2_TOPK = 5
FORMAL_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK = 64
FORMAL_EXACT_SCOREINFO_GPU_MAX_PER_TASK = 512
FORMAL_GASAL2_ENV_OVERRIDES = {
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
    "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
    "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": str(
        FORMAL_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK
    ),
    "FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE": "1",
    "FASIM_PREALIGN_CUDA_MAX_TASKS": "16384",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU": "1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK": str(
        FORMAL_EXACT_SCOREINFO_GPU_MAX_PER_TASK
    ),
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT": "1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT": "1",
    "FASIM_OUTPUT_TOPK_LITE": str(FORMAL_GASAL2_TOPK),
}
FORMAL_GASAL2_FORBIDDEN_ENV_PREFIXES = (
    "FASIM_TOP5_GASAL2_LONG_QUERY_",
)
FORMAL_GASAL2_ALLOWED_EXTRA_ENV = {
    "FASIM_ALIGN_GASAL2_BATCH",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN",
    "FASIM_ALIGN_GASAL2_STREAMS",
    "FASIM_TOP5_GASAL2_SCOREINFO_EMIT_RANK_OBSERVE",
    "FASIM_VERBOSE",
}
FORMAL_GASAL2_REQUIRED_PER_SHARD_BENCHMARKS = (
    "fasim_top5_gasal2_gpu_scoreinfo_requested",
    "fasim_top5_gasal2_gpu_scoreinfo_active",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled",
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled",
)
FORMAL_GASAL2_REQUIRED_POSITIVE_BENCHMARKS = (
    "fasim_gasal2_requests",
    "fasim_gasal2_score_requests",
    "fasim_gasal2_traceback_requests",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks",
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows",
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank",
)
FORMAL_GASAL2_REQUIRED_ZERO_BENCHMARKS = (
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
    "fasim_gasal2_fallbacks",
    "fasim_gasal2_length_guard_fallbacks",
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows",
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} is not a JSON object")
    return payload


def _resolve_path(raw_path: object, *, base_dir: Path, field: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise RuntimeError(f"{field} is missing or not a path")
    path = Path(raw_path)
    if not path.is_absolute():
        path = base_dir / path
    return path


def _check_hex_digest(payload: dict[str, Any], field: str) -> str:
    digest = payload.get(field)
    if not isinstance(digest, str) or len(digest) != 64:
        raise RuntimeError(f"{field} is missing or not a SHA-256 digest")
    return digest


def _is_integer_sort_value(value: str) -> bool:
    if not value:
        return False
    if value[0] == "-":
        return len(value) > 1 and value[1:].isdigit()
    return value.isdigit()


def _convert_sort_value(value: str) -> tuple[int, object]:
    if _is_integer_sort_value(value):
        return (0, int(value))
    try:
        return (1, float(value))
    except ValueError:
        return (2, value)


def _lite_sort_key(header: str, row: str) -> tuple[Any, ...]:
    positions = {
        name: index
        for index, name in enumerate(header.split("\t"))
        if name in CANONICAL_SORT_COLUMNS
    }
    parts = row.split("\t")
    key: list[object] = []
    for name in CANONICAL_SORT_COLUMNS:
        index = positions.get(name)
        if index is not None and index < len(parts):
            key.append((name, _convert_sort_value(parts[index])))
    key.append(("row", row))
    return tuple(key)


def _check_artifact(
    payload: dict[str, Any],
    *,
    base_dir: Path,
    contract: str,
    output_field: str,
    digest_field: str,
    payload_digest_field: str,
) -> dict[str, str]:
    artifact_path = _resolve_path(
        payload.get(output_field),
        base_dir=base_dir,
        field=output_field,
    )
    if not artifact_path.exists():
        raise RuntimeError(f"artifact does not exist: {artifact_path}")

    content = artifact_path.read_text(encoding="utf-8")
    if "\n" not in content:
        raise RuntimeError(f"artifact has no payload: {artifact_path}")
    first_line, artifact_payload = content.split("\n", 1)
    expected_first_line = f"# result_contract={contract}"
    if first_line != expected_first_line:
        raise RuntimeError(
            "artifact contract line mismatch: "
            f"expected {expected_first_line!r}, got {first_line!r}"
        )
    payload_lines = artifact_payload.splitlines()
    if not payload_lines or not payload_lines[0].startswith("mode\trank\t"):
        raise RuntimeError("artifact payload header is missing")

    expected_full_digest = _check_hex_digest(payload, digest_field)
    expected_payload_digest = _check_hex_digest(payload, payload_digest_field)
    full_digest = _sha256_text(content)
    payload_digest = _sha256_text(artifact_payload)
    if full_digest != expected_full_digest:
        raise RuntimeError(
            f"{digest_field} does not match artifact content: "
            f"{expected_full_digest} != {full_digest}"
        )
    if payload_digest != expected_payload_digest:
        raise RuntimeError(
            f"{payload_digest_field} does not match artifact payload: "
            f"{expected_payload_digest} != {payload_digest}"
        )
    return {
        "artifact_path": str(artifact_path),
        "full_digest": full_digest,
        "payload_digest": payload_digest,
        "payload": artifact_payload,
    }


def _expected_topk_lite_from_rows_artifact(rows_payload: str) -> tuple[str, list[str]]:
    lines = rows_payload.splitlines()
    if not lines:
        raise RuntimeError("topK rows artifact payload is empty")
    header_parts = lines[0].split("\t")
    if len(header_parts) < 3 or header_parts[0] != "mode" or header_parts[1] != "rank":
        raise RuntimeError("topK rows artifact header is invalid")
    lite_header = "\t".join(header_parts[2:])
    rows = []
    for line in lines[1:]:
        parts = line.split("\t", 2)
        if len(parts) != 3:
            raise RuntimeError("topK rows artifact row is invalid")
        rows.append(parts[2])
    unique_rows = sorted(set(rows), key=lambda row: _lite_sort_key(lite_header, row))
    return lite_header, unique_rows


def _check_rows_match_summary_artifact(summary_payload: str, rows_payload: str) -> None:
    if summary_payload.splitlines() != rows_payload.splitlines():
        raise RuntimeError("topK rows artifact rows do not match topK summary artifact")


def _topk_digest(keys: list[str]) -> str:
    return _sha256_text("\n".join(keys) + "\n")


def _expected_topk_summary_object(
    *,
    summary_payload: str,
    rows_payload: str,
    k: int,
) -> dict[str, Any]:
    summary_lines = summary_payload.splitlines()
    rows_lines = rows_payload.splitlines()
    if not summary_lines or not rows_lines:
        raise RuntimeError("topK artifact payload is empty")
    summary_header = summary_lines[0].split("\t")
    rows_header = rows_lines[0].split("\t")
    if (
        len(summary_header) < 3
        or summary_header[0] != "mode"
        or summary_header[1] != "rank"
    ):
        raise RuntimeError("topK summary artifact header is invalid")
    if len(rows_header) < 3 or rows_header[0] != "mode" or rows_header[1] != "rank":
        raise RuntimeError("topK rows artifact header is invalid")
    header = "\t".join(rows_header[2:])
    modes: dict[str, dict[str, Any]] = {
        mode: {"digest": _topk_digest([]), "keys": [], "rows": []}
        for mode in TOPK_MODES
    }
    for summary_line, rows_line in zip(summary_lines[1:], rows_lines[1:], strict=True):
        summary_parts = summary_line.split("\t", 2)
        rows_parts = rows_line.split("\t", 2)
        if len(summary_parts) != 3 or len(rows_parts) != 3:
            raise RuntimeError("topK artifact row is invalid")
        summary_mode, summary_rank_text, key = summary_parts
        rows_mode, rows_rank_text, row = rows_parts
        if summary_mode != rows_mode or summary_rank_text != rows_rank_text:
            raise RuntimeError("topK summary and rows artifact rank mismatch")
        if summary_mode not in modes:
            raise RuntimeError(f"topK artifact has unexpected mode: {summary_mode}")
        try:
            rank = int(summary_rank_text)
        except ValueError as exc:
            raise RuntimeError("topK artifact rank is not an integer") from exc
        if rank != len(modes[summary_mode]["keys"]) + 1:
            raise RuntimeError("topK artifact ranks are not contiguous")
        modes[summary_mode]["keys"].append(key)
        modes[summary_mode]["rows"].append(row)
    for mode, payload in modes.items():
        if len(payload["keys"]) > k:
            raise RuntimeError(f"topK artifact has too many rows for mode: {mode}")
        payload["digest"] = _topk_digest(payload["keys"])
    return {
        "k": k,
        "header": header,
        "modes": modes,
    }


def _check_topk_summary_object(
    report: dict[str, Any],
    *,
    summary_payload: str,
    rows_payload: str,
) -> None:
    topk_summary = report.get("topk_summary")
    if not isinstance(topk_summary, dict):
        raise RuntimeError("report topk_summary is missing or invalid")
    k = topk_summary.get("k")
    if not isinstance(k, int) or k < 1:
        raise RuntimeError("report topk_summary k is missing or invalid")
    rows_considered = topk_summary.get("rows_considered")
    if not isinstance(rows_considered, int) or rows_considered < 0:
        raise RuntimeError("report topk_summary rows_considered is missing or invalid")
    expected = _expected_topk_summary_object(
        summary_payload=summary_payload,
        rows_payload=rows_payload,
        k=k,
    )
    comparable = {
        "k": topk_summary.get("k"),
        "header": topk_summary.get("header"),
        "modes": topk_summary.get("modes"),
    }
    if comparable != expected:
        raise RuntimeError("topk_summary object does not match topK summary artifact")


def _number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key, 0)
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    raise RuntimeError(f"formal GASAL2 benchmark {key} is not numeric")


def _check_formal_gasal2_env(
    payload: dict[str, Any],
    *,
    field: str,
    label: str,
) -> None:
    env = payload.get(field)
    if not isinstance(env, dict):
        raise RuntimeError(f"formal GASAL2 {label} requires {field}")
    for key, expected in FORMAL_GASAL2_ENV_OVERRIDES.items():
        if env.get(key) != expected:
            raise RuntimeError(
                f"formal GASAL2 {label} {field} missing {key}={expected}"
            )
    allowed = set(FORMAL_GASAL2_ENV_OVERRIDES) | FORMAL_GASAL2_ALLOWED_EXTRA_ENV
    for key in sorted(env):
        if any(key.startswith(prefix) for prefix in FORMAL_GASAL2_FORBIDDEN_ENV_PREFIXES):
            raise RuntimeError(
                f"formal GASAL2 {label} {field} contains forbidden "
                f"segmented diagnostic env {key}"
            )
        if key not in allowed:
            raise RuntimeError(
                f"formal GASAL2 {label} {field} contains unsupported formal env {key}"
            )
    _check_formal_gasal2_numeric_env(
        env,
        "FASIM_ALIGN_GASAL2_BATCH",
        label=label,
        field=field,
        maximum=FORMAL_GASAL2_MAX_BATCH,
    )
    _check_formal_gasal2_numeric_env(
        env,
        "FASIM_ALIGN_GASAL2_STREAMS",
        label=label,
        field=field,
        maximum=FORMAL_GASAL2_MAX_STREAMS,
    )
    _check_formal_gasal2_numeric_env(
        env,
        "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN",
        label=label,
        field=field,
        maximum=FORMAL_GASAL2_MAX_QUERY_LEN,
    )


def _check_formal_gasal2_numeric_env(
    env: dict[str, Any],
    key: str,
    *,
    label: str,
    field: str,
    maximum: int,
) -> None:
    value = env.get(key)
    if value is None:
        return
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"formal GASAL2 {label} {field} {key} must be an integer"
        ) from exc
    if parsed <= 0:
        raise RuntimeError(
            f"formal GASAL2 {label} {field} {key} must be positive"
        )
    if parsed > maximum:
        raise RuntimeError(
            f"formal GASAL2 {label} {field} {key} exceeds checked limit {maximum}"
        )


def _check_formal_gasal2_query_max_env(
    payload: dict[str, Any],
    *,
    field: str,
    label: str,
    recorded_max_query_len: int,
) -> None:
    env = payload.get(field)
    if not isinstance(env, dict):
        raise RuntimeError(f"formal GASAL2 {label} requires {field}")
    value = env.get("FASIM_ALIGN_GASAL2_MAX_QUERY_LEN")
    if value is None:
        return
    if int(value) != recorded_max_query_len:
        raise RuntimeError(
            "formal GASAL2 "
            f"{label} {field} FASIM_ALIGN_GASAL2_MAX_QUERY_LEN "
            "does not match recorded query preflight max"
        )


def _check_formal_gasal2_benchmarks(report: dict[str, Any]) -> None:
    shard_count = report.get("shard_count")
    benchmark_shards = report.get("fasim_benchmark_shards")
    benchmark_sums = report.get("fasim_benchmark_sums")
    if not isinstance(shard_count, int) or shard_count <= 0:
        raise RuntimeError("formal GASAL2 artifact requires positive shard_count")
    if benchmark_shards != shard_count:
        raise RuntimeError(
            "formal GASAL2 artifact benchmark shard count mismatch: "
            f"benchmark_shards={benchmark_shards} shard_count={shard_count}"
        )
    if not isinstance(benchmark_sums, dict):
        raise RuntimeError("formal GASAL2 artifact requires fasim_benchmark_sums")
    for key in FORMAL_GASAL2_REQUIRED_PER_SHARD_BENCHMARKS:
        value = _number(benchmark_sums, key)
        if value != float(shard_count):
            raise RuntimeError(
                "formal GASAL2 artifact requires per-shard "
                f"{key}={shard_count}, got {value:g}"
            )
    for key in FORMAL_GASAL2_REQUIRED_POSITIVE_BENCHMARKS:
        value = _number(benchmark_sums, key)
        if value <= 0.0:
            raise RuntimeError(
                f"formal GASAL2 artifact requires positive {key}, got {value:g}"
            )
    for key in FORMAL_GASAL2_REQUIRED_ZERO_BENCHMARKS:
        value = _number(benchmark_sums, key)
        if value != 0.0:
            raise RuntimeError(
                f"formal GASAL2 artifact requires zero {key}, got {value:g}"
            )


def _check_contract_state(report: dict[str, Any], *, contract: str) -> None:
    if contract == "gasal2_top5_column_pruned_scoreinfo_artifact_v1":
        if report.get("run_status") != "completed":
            raise RuntimeError("formal GASAL2 topK artifact requires completed run")
        if report.get("topk_summary_only") is not True:
            raise RuntimeError("formal GASAL2 topK artifact requires topk_summary_only")
        if report.get("shard_output_topk_lite") != FORMAL_GASAL2_TOPK:
            raise RuntimeError("formal GASAL2 topK artifact requires topK-lite 5")
        topk_summary = report.get("topk_summary")
        if not isinstance(topk_summary, dict) or topk_summary.get("k") != FORMAL_GASAL2_TOPK:
            raise RuntimeError("formal GASAL2 topK artifact requires topK summary k=5")
        if report.get("gasal2_top5_column_pruned_scoreinfo") is not True:
            raise RuntimeError("formal GASAL2 artifact requires column-pruned preset flag")
        if (
            report.get("gasal2_top5_scoreinfo_prune_max_per_task")
            != FORMAL_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK
        ):
            raise RuntimeError("formal GASAL2 artifact requires scoreInfo prune cap 64")
        if (
            report.get("exact_scoreinfo_gpu_max_per_task")
            != FORMAL_EXACT_SCOREINFO_GPU_MAX_PER_TASK
        ):
            raise RuntimeError("formal GASAL2 artifact requires exact scoreInfo max-per-task 512")
        if report.get("exact_scoreinfo_gpu_pruned_output") is not True:
            raise RuntimeError("formal GASAL2 artifact requires exact scoreInfo pruned output")
        if report.get("exact_scoreinfo_gpu_column_pruned_output") is not True:
            raise RuntimeError(
                "formal GASAL2 artifact requires exact scoreInfo column-pruned output"
            )
        _check_formal_gasal2_env(report, field="env_overrides", label="artifact")
        if report.get("gasal2_top5_activation_verified") is not True:
            raise RuntimeError(
                "formal GASAL2 topK artifact requires verified activation"
            )
        if report.get("gasal2_top5_activation_error") is not None:
            raise RuntimeError(
                "formal GASAL2 topK artifact activation error must be empty"
            )
        if report.get("gasal2_top5_query_preflight_supported") is not True:
            raise RuntimeError(
                "formal GASAL2 topK artifact requires verified query preflight"
            )
        if report.get("gasal2_top5_query_preflight_error") is not None:
            raise RuntimeError(
                "formal GASAL2 topK artifact query preflight error must be empty"
            )
        query_len = report.get("gasal2_top5_query_preflight_query_len")
        max_query_len = report.get("gasal2_top5_query_preflight_max_query_len")
        if not isinstance(query_len, int) or query_len < 0:
            raise RuntimeError(
                "formal GASAL2 query preflight query length is missing or invalid"
            )
        if not isinstance(max_query_len, int) or max_query_len <= 0:
            raise RuntimeError(
                "formal GASAL2 query preflight max query length is missing or invalid"
            )
        if max_query_len > FORMAL_GASAL2_MAX_QUERY_LEN:
            raise RuntimeError(
                "formal GASAL2 query preflight max query length exceeds checked limit"
            )
        if query_len > max_query_len:
            raise RuntimeError("formal GASAL2 query preflight length exceeds max")
        _check_formal_gasal2_query_max_env(
            report,
            field="env_overrides",
            label="artifact",
            recorded_max_query_len=max_query_len,
        )
        _check_formal_gasal2_benchmarks(report)


def _check_report(report_path: Path) -> dict[str, Any]:
    report = _load_json(report_path)
    contract = report.get("result_contract")
    if not isinstance(contract, str) or not contract:
        raise RuntimeError("report result_contract is missing")
    _check_contract_state(report, contract=contract)

    summary = _check_artifact(
        report,
        base_dir=report_path.parent,
        contract=contract,
        output_field="topk_summary_output",
        digest_field="topk_summary_digest",
        payload_digest_field="topk_summary_payload_digest",
    )
    rows = _check_artifact(
        report,
        base_dir=report_path.parent,
        contract=contract,
        output_field="topk_rows_output",
        digest_field="topk_rows_digest",
        payload_digest_field="topk_rows_payload_digest",
    )
    _check_rows_match_summary_artifact(summary["payload"], rows["payload"])
    _check_topk_summary_object(
        report,
        summary_payload=summary["payload"],
        rows_payload=rows["payload"],
    )
    topk_lite_output = _resolve_path(
        report.get("topk_lite_output"),
        base_dir=report_path.parent,
        field="topk_lite_output",
    )
    if not topk_lite_output.exists():
        raise RuntimeError(f"topK lite artifact does not exist: {topk_lite_output}")
    topk_lite_digest = hashlib.sha256(topk_lite_output.read_bytes()).hexdigest()
    expected_topk_lite_digest = _check_hex_digest(report, "topk_lite_digest")
    if topk_lite_digest != expected_topk_lite_digest:
        raise RuntimeError(
            "topk_lite_digest does not match artifact content: "
            f"{expected_topk_lite_digest} != {topk_lite_digest}"
        )
    topk_lite_records = report.get("topk_lite_records")
    if not isinstance(topk_lite_records, int) or topk_lite_records < 0:
        raise RuntimeError("topk_lite_records is missing or invalid")
    lite_lines = topk_lite_output.read_text(encoding="utf-8").splitlines()
    if not lite_lines or not lite_lines[0].startswith("Chr\tStartInGenome\t"):
        raise RuntimeError("topK lite artifact header is missing")
    if len(lite_lines) != topk_lite_records + 1:
        raise RuntimeError("topK lite artifact record count does not match report")
    expected_header, expected_rows = _expected_topk_lite_from_rows_artifact(rows["payload"])
    if lite_lines[0] != expected_header or lite_lines[1:] != expected_rows:
        raise RuntimeError("topK lite artifact rows do not match topK rows artifact")

    return {
        "contract": contract,
        "artifact_path": summary["artifact_path"],
        "full_digest": summary["full_digest"],
        "payload_digest": summary["payload_digest"],
        "rows_artifact_path": rows["artifact_path"],
        "rows_full_digest": rows["full_digest"],
        "rows_payload_digest": rows["payload_digest"],
        "topk_lite_artifact_path": str(topk_lite_output),
        "topk_lite_digest": topk_lite_digest,
        "topk_lite_records": topk_lite_records,
        "gasal2_top5_query_preflight_supported": report.get(
            "gasal2_top5_query_preflight_supported"
        ),
        "gasal2_top5_query_preflight_error": report.get(
            "gasal2_top5_query_preflight_error"
        ),
        "gasal2_top5_query_preflight_query_len": report.get(
            "gasal2_top5_query_preflight_query_len"
        ),
        "gasal2_top5_query_preflight_max_query_len": report.get(
            "gasal2_top5_query_preflight_max_query_len"
        ),
    }


def _check_manifest(
    manifest_path: Path,
    *,
    report_check: dict[str, Any],
) -> None:
    manifest = _load_json(manifest_path)
    if manifest.get("result_contract") != report_check["contract"]:
        raise RuntimeError("manifest result_contract does not match report")
    if report_check["contract"] == "gasal2_top5_column_pruned_scoreinfo_artifact_v1":
        if manifest.get("run_status") != "completed":
            raise RuntimeError("formal GASAL2 manifest requires completed run")
        _check_formal_gasal2_env(manifest, field="env_snapshot", label="manifest")
        if manifest.get("gasal2_top5_activation_verified") is not True:
            raise RuntimeError("formal GASAL2 manifest requires verified activation")
        if manifest.get("gasal2_top5_activation_error") is not None:
            raise RuntimeError("formal GASAL2 manifest activation error must be empty")
        if manifest.get("gasal2_top5_query_preflight_supported") is not True:
            raise RuntimeError(
                "formal GASAL2 manifest requires verified query preflight"
            )
        if manifest.get("gasal2_top5_query_preflight_error") is not None:
            raise RuntimeError(
                "formal GASAL2 manifest query preflight error must be empty"
            )
        for field in (
            "gasal2_top5_query_preflight_supported",
            "gasal2_top5_query_preflight_error",
            "gasal2_top5_query_preflight_query_len",
            "gasal2_top5_query_preflight_max_query_len",
        ):
            if manifest.get(field) != report_check[field]:
                raise RuntimeError(
                    "formal GASAL2 manifest query preflight fields do not match report"
                )
        _check_formal_gasal2_query_max_env(
            manifest,
            field="env_snapshot",
            label="manifest",
            recorded_max_query_len=manifest["gasal2_top5_query_preflight_max_query_len"],
        )

    manifest_output = _resolve_path(
        manifest.get("topk_summary_output"),
        base_dir=manifest_path.parent,
        field="manifest topk_summary_output",
    )
    if str(manifest_output) != str(Path(str(report_check["artifact_path"]))):
        raise RuntimeError("manifest topk_summary_output does not match report")
    if manifest.get("topk_summary_digest") != report_check["full_digest"]:
        raise RuntimeError("manifest topk_summary_digest does not match report/artifact")
    if manifest.get("topk_summary_payload_digest") != report_check["payload_digest"]:
        raise RuntimeError(
            "manifest topk_summary_payload_digest does not match report/artifact"
        )
    manifest_rows_output = _resolve_path(
        manifest.get("topk_rows_output"),
        base_dir=manifest_path.parent,
        field="manifest topk_rows_output",
    )
    if str(manifest_rows_output) != str(Path(str(report_check["rows_artifact_path"]))):
        raise RuntimeError("manifest topk_rows_output does not match report")
    if manifest.get("topk_rows_digest") != report_check["rows_full_digest"]:
        raise RuntimeError("manifest topk_rows_digest does not match report/artifact")
    if manifest.get("topk_rows_payload_digest") != report_check["rows_payload_digest"]:
        raise RuntimeError("manifest topk_rows_payload_digest does not match report/artifact")
    manifest_lite_output = _resolve_path(
        manifest.get("topk_lite_output"),
        base_dir=manifest_path.parent,
        field="manifest topk_lite_output",
    )
    if str(manifest_lite_output) != str(Path(str(report_check["topk_lite_artifact_path"]))):
        raise RuntimeError("manifest topk_lite_output does not match report")
    if manifest.get("topk_lite_digest") != report_check["topk_lite_digest"]:
        raise RuntimeError("manifest topk_lite_digest does not match report/artifact")
    if manifest.get("topk_lite_records") != report_check["topk_lite_records"]:
        raise RuntimeError("manifest topk_lite_records does not match report")


def _check_same_payload(
    *,
    report_check: dict[str, Any],
    other_report_path: Path,
) -> None:
    other_check = _check_report(other_report_path)
    if report_check["payload_digest"] != other_check["payload_digest"]:
        raise RuntimeError(
            "topK payload digest mismatch: "
            f"{report_check['payload_digest']} != {other_check['payload_digest']} "
            f"for {other_report_path}"
        )


def _check_different_full_digest(
    *,
    report_check: dict[str, Any],
    other_report_path: Path,
) -> None:
    other_check = _check_report(other_report_path)
    if report_check["full_digest"] == other_check["full_digest"]:
        raise RuntimeError(
            "topK full artifact digests unexpectedly match across contracts: "
            f"{report_check['full_digest']} for {other_report_path}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify topK summary artifact digests in report/manifest JSON."
    )
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--same-payload-as",
        action="append",
        default=[],
        type=Path,
        help="Require this report's payload digest to match another report.",
    )
    parser.add_argument(
        "--different-full-digest-from",
        action="append",
        default=[],
        type=Path,
        help="Require this report's full artifact digest to differ from another report.",
    )
    args = parser.parse_args(argv)

    try:
        report_check = _check_report(args.report)
        if args.manifest is not None:
            _check_manifest(args.manifest, report_check=report_check)
        for other_report_path in args.same_payload_as:
            _check_same_payload(
                report_check=report_check,
                other_report_path=other_report_path,
            )
        for other_report_path in args.different_full_digest_from:
            _check_different_full_digest(
                report_check=report_check,
                other_report_path=other_report_path,
            )
    except Exception as exc:
        print(f"check_topk_summary_digest_integrity: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
