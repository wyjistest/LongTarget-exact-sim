#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


PREFIX = "benchmark.fasim_gasal2_traceback_certificate_shadow_"

INTEGER_METRICS = (
    "requested",
    "active",
    "real_skip_enabled",
    "pre_drop_proof_available",
    "candidates_considered",
    "certified_skips",
    "uncertified_candidates",
    "exact_descriptor_duplicate_skips",
    "static_span_skips",
    "score_endpoint_span_skips",
    "shadow_false_rejects",
    "score_frontier_skips",
    "stability_frontier_skips",
    "nt_frontier_skips",
    "tie_rescues",
    "rank_aware_supported",
    "probe_requests",
    "fallbacks",
)

FIELDS = (
    "workload",
    "status",
    "decision",
    "query",
    "target",
    "scope",
    "output_contract",
    "logs",
    "authority_traceback_requests",
    "candidates_considered",
    "certified_skips",
    "certified_fraction",
    "uncertified_candidates",
    "exact_descriptor_duplicate_skips",
    "static_span_skips",
    "score_endpoint_span_skips",
    "shadow_false_rejects",
    "score_frontier_skips",
    "stability_frontier_skips",
    "nt_frontier_skips",
    "tie_rescues",
    "rank_aware_supported",
    "pre_drop_proof_available",
    "proof_version",
    "real_skip_enabled",
    "probe_requests",
    "probe_seconds",
    "certificate_fallbacks",
    "authority_fallbacks",
    "length_guard_fallbacks",
    "artifact_provenance",
)


class SummaryError(ValueError):
    pass


def parse_log(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    required = [PREFIX + name for name in INTEGER_METRICS]
    required.extend(
        [
            PREFIX + "proof_version",
            PREFIX + "probe_seconds",
            "benchmark.fasim_gasal2_traceback_requests",
            "benchmark.fasim_gasal2_fallbacks",
            "benchmark.fasim_gasal2_length_guard_fallbacks",
        ]
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise SummaryError(f"missing required metrics in {path}: {missing}")
    return values


def integer(values: dict[str, str], key: str, path: Path) -> int:
    try:
        parsed = int(values[key])
    except ValueError as exc:
        raise SummaryError(f"invalid integer {key}={values[key]!r} in {path}") from exc
    if parsed < 0:
        raise SummaryError(f"invalid non-negative {key}={parsed} in {path}")
    return parsed


def floating(values: dict[str, str], key: str, path: Path) -> float:
    try:
        parsed = float(values[key])
    except ValueError as exc:
        raise SummaryError(f"invalid float {key}={values[key]!r} in {path}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise SummaryError(f"invalid non-negative {key}={parsed} in {path}")
    return parsed


def validate_log(path: Path, values: dict[str, str]) -> None:
    metrics = {name: integer(values, PREFIX + name, path) for name in INTEGER_METRICS}
    considered = metrics["candidates_considered"]
    certified = metrics["certified_skips"]
    reasons = (
        metrics["exact_descriptor_duplicate_skips"]
        + metrics["static_span_skips"]
        + metrics["score_endpoint_span_skips"]
    )
    if metrics["requested"] != 1 or metrics["active"] != 1:
        raise SummaryError(f"certificate shadow inactive in {path}")
    if metrics["real_skip_enabled"] != 0:
        raise SummaryError(f"real traceback skip unexpectedly enabled in {path}")
    if metrics["pre_drop_proof_available"] != 1:
        raise SummaryError(f"pre-drop proof unavailable in {path}")
    if metrics["rank_aware_supported"] != 0:
        raise SummaryError(f"unexpected rank-aware support claim in {path}")
    if certified + metrics["uncertified_candidates"] != considered:
        raise SummaryError(f"candidate accounting does not close in {path}")
    if reasons != certified:
        raise SummaryError(f"certificate reason accounting does not close in {path}")
    if metrics["probe_requests"] != considered:
        raise SummaryError(f"probe request accounting does not close in {path}")
    if integer(values, "benchmark.fasim_gasal2_traceback_requests", path) != considered:
        raise SummaryError(f"authority traceback requests do not match considered in {path}")
    if metrics["shadow_false_rejects"] != 0:
        raise SummaryError(f"shadow_false_rejects must be zero in {path}")
    if metrics["fallbacks"] != 0:
        raise SummaryError(f"certificate fallback detected in {path}")
    if integer(values, "benchmark.fasim_gasal2_fallbacks", path) != 0:
        raise SummaryError(f"authority fallback detected in {path}")
    if integer(values, "benchmark.fasim_gasal2_length_guard_fallbacks", path) != 0:
        raise SummaryError(f"length guard fallback detected in {path}")
    floating(values, PREFIX + "probe_seconds", path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize exact pre-traceback certificate shadow telemetry."
    )
    parser.add_argument("--workload", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--output-contract", required=True)
    parser.add_argument("--stderr", required=True, action="append", type=Path)
    parser.add_argument("--artifact-provenance", default="")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    parsed: list[tuple[Path, dict[str, str]]] = []
    for path in args.stderr:
        values = parse_log(path)
        validate_log(path, values)
        parsed.append((path, values))

    def total_shadow(name: str) -> int:
        return sum(integer(values, PREFIX + name, path) for path, values in parsed)

    def total_benchmark(name: str) -> int:
        key = "benchmark." + name
        return sum(integer(values, key, path) for path, values in parsed)

    considered = total_shadow("candidates_considered")
    certified = total_shadow("certified_skips")
    fraction = certified / considered if considered else 0.0
    if certified == 0:
        decision = "no_go_zero_certified_skips"
    elif fraction < 0.20:
        decision = "no_go_below_request_reduction_gate"
    else:
        decision = "shadow_material_requires_runtime_gate"
    proof_versions = {values[PREFIX + "proof_version"] for _, values in parsed}
    if len(proof_versions) != 1:
        raise SummaryError(f"mixed proof versions: {sorted(proof_versions)}")

    row: dict[str, str | int] = {
        "workload": args.workload,
        "status": "complete",
        "decision": decision,
        "query": args.query,
        "target": args.target,
        "scope": args.scope,
        "output_contract": args.output_contract,
        "logs": len(parsed),
        "authority_traceback_requests": total_benchmark("fasim_gasal2_traceback_requests"),
        "candidates_considered": considered,
        "certified_skips": certified,
        "certified_fraction": f"{fraction:.6f}",
        "uncertified_candidates": total_shadow("uncertified_candidates"),
        "exact_descriptor_duplicate_skips": total_shadow(
            "exact_descriptor_duplicate_skips"
        ),
        "static_span_skips": total_shadow("static_span_skips"),
        "score_endpoint_span_skips": total_shadow("score_endpoint_span_skips"),
        "shadow_false_rejects": total_shadow("shadow_false_rejects"),
        "score_frontier_skips": total_shadow("score_frontier_skips"),
        "stability_frontier_skips": total_shadow("stability_frontier_skips"),
        "nt_frontier_skips": total_shadow("nt_frontier_skips"),
        "tie_rescues": total_shadow("tie_rescues"),
        "rank_aware_supported": total_shadow("rank_aware_supported"),
        "pre_drop_proof_available": min(
            integer(values, PREFIX + "pre_drop_proof_available", path)
            for path, values in parsed
        ),
        "proof_version": next(iter(proof_versions)),
        "real_skip_enabled": total_shadow("real_skip_enabled"),
        "probe_requests": total_shadow("probe_requests"),
        "probe_seconds": f"{sum(floating(values, PREFIX + 'probe_seconds', path) for path, values in parsed):.6f}",
        "certificate_fallbacks": total_shadow("fallbacks"),
        "authority_fallbacks": total_benchmark("fasim_gasal2_fallbacks"),
        "length_guard_fallbacks": total_benchmark("fasim_gasal2_length_guard_fallbacks"),
        "artifact_provenance": args.artifact_provenance
        or ",".join(str(path) for path, _ in parsed),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(row)
    print("".join(f"{field}={row[field]}\n" for field in FIELDS), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, SummaryError) as exc:
        raise SystemExit(str(exc)) from exc
