#!/usr/bin/env python3
"""Preflight or analyze the frozen biological Top-K fresh holdout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import (
        compare_candidate_topk,
        contract,
        exact_binomial_bounds,
        freeze_fresh_holdout as frozen,
        run_fresh_holdout as runner,
    )
except ImportError:  # pragma: no cover
    import compare_candidate_topk  # type: ignore[no-redef]
    import contract  # type: ignore[no-redef]
    import exact_binomial_bounds  # type: ignore[no-redef]
    import freeze_fresh_holdout as frozen  # type: ignore[no-redef]
    import run_fresh_holdout as runner  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
SOURCE_DATA = PAPER / "source_data"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout"
COMPARISON_ROOT = ARTIFACT_ROOT / "offline-comparisons"
MATCHES_PATH = SOURCE_DATA / "fresh_candidate_matches.tsv"
WORKLOAD_METRICS_PATH = SOURCE_DATA / "fresh_workload_metrics.tsv"
EMPTY_PATH = SOURCE_DATA / "fresh_empty_workloads.tsv"
FAILURE_PATH = SOURCE_DATA / "fresh_failure_ledger.tsv"
BOUNDS_PATH = SOURCE_DATA / "fresh_exact_binomial_bounds.tsv"
RANK_PATH = SOURCE_DATA / "fresh_rank_diagnostics.tsv"
RECEIPT_PATH = PAPER / "fresh_holdout_receipt.json"
DECISION_PATH = PAPER / "fresh_holdout_decision.json"

MATCH_FIELDS = (
    "validation_instance_id",
    "repeat_id",
    "primary_instance",
    *compare_candidate_topk.DETAIL_FIELDS,
)
WORKLOAD_FIELDS = (
    "validation_instance_id",
    "workload_id",
    "repeat_id",
    "primary_instance",
    "ranking_mode",
    "comparison_status",
    "reference_candidate_count",
    "candidate_candidate_count",
    "matched_count",
    "informative_for_recovery",
    "binary_gate_denominator_eligible",
    "binary_success",
    "double_empty",
    "recall",
    "precision",
    "top1_retained",
    "complete_set_success",
    "rbo5_diagnostic",
    "ambiguous_matching",
    "technical_failure",
    "technical_failure_reason",
    "input_identity_pass",
    "matching_started",
    "strict_row_equal",
    "classifications",
    "evidence_role",
)
EMPTY_FIELDS = (
    "validation_instance_id",
    "workload_id",
    "repeat_id",
    "primary_instance",
    "authority_candidate_count_score",
    "candidate_candidate_count_score",
    "clean_double_empty_all_modes",
    "binary_gate_denominator_eligible",
    "evidence_role",
)
FAILURE_FIELDS = (
    "failure_id",
    "validation_instance_id",
    "workload_id",
    "repeat_id",
    "primary_instance",
    "attempt_id",
    "arm",
    "failure_class",
    "failure_reason",
    "missing_output",
    "input_identity_mismatch",
    "ambiguous_matching",
    "unexpected_fallback",
    "retained_in_binary_denominator",
    "replacement_or_retry_used",
    "evidence_role",
)
BOUND_FIELDS = (
    "endpoint_order",
    "endpoint_name",
    "ranking_mode",
    "successes",
    "trials",
    "estimate",
    "alpha_one_sided",
    "lower_confidence_bound",
    "promotion_threshold",
    "threshold_pass",
    "method",
    "fixed_sequence_gate_reached",
)
RANK_FIELDS = (
    "validation_instance_id",
    "workload_id",
    "repeat_id",
    "primary_instance",
    "ranking_mode",
    "depth",
    "persistence",
    "finite_rbo_fraction",
    "finite_rbo_decimal",
    "rank_displacements_json",
    "claim_role",
)


class AnalysisError(RuntimeError):
    """Raised for a fail-closed analysis precondition or artifact error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError(message)


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def scalar(value: Any) -> Any:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list, tuple)):
        return compact_json(value)
    return value


def render_tsv(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: scalar(row.get(field)) for field in fields})
    return output.getvalue().encode("utf-8")


def attempt_receipts(attempts: Sequence[Mapping[str, str]]) -> tuple[dict[str, dict[str, Any]], list[Mapping[str, str]]]:
    receipts: dict[str, dict[str, Any]] = {}
    missing = []
    for row in attempts:
        root = ROOT / row["artifact_root"]
        receipt_path = root / "attempt-complete.json"
        if not receipt_path.is_file():
            missing.append(row)
            continue
        receipt = runner.validate_completed_attempt(root, row)
        receipts[row["attempt_id"]] = receipt
    return receipts, missing


def failure_row(
    *,
    failure_id: str,
    validation_id: str,
    workload_id: str,
    repeat_id: int,
    primary: bool,
    attempt_id: str,
    arm: str,
    failure_class: str,
    reason: str,
    missing_output: bool = False,
    input_mismatch: bool = False,
    ambiguous: bool = False,
    fallback: bool = False,
) -> dict[str, Any]:
    return {
        "failure_id": failure_id,
        "validation_instance_id": validation_id,
        "workload_id": workload_id,
        "repeat_id": repeat_id,
        "primary_instance": primary,
        "attempt_id": attempt_id,
        "arm": arm,
        "failure_class": failure_class,
        "failure_reason": reason,
        "missing_output": missing_output,
        "input_identity_mismatch": input_mismatch,
        "ambiguous_matching": ambiguous,
        "unexpected_fallback": fallback,
        "retained_in_binary_denominator": primary,
        "replacement_or_retry_used": False,
        "evidence_role": "fresh_concordance_promotion",
    }


def technical_metric(
    *,
    validation_id: str,
    workload_id: str,
    repeat_id: int,
    primary: bool,
    mode: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "validation_instance_id": validation_id,
        "workload_id": workload_id,
        "repeat_id": repeat_id,
        "primary_instance": primary,
        "ranking_mode": mode,
        "comparison_status": "technical_failure",
        "reference_candidate_count": "NA",
        "candidate_candidate_count": "NA",
        "matched_count": 0,
        "informative_for_recovery": "NA",
        "binary_gate_denominator_eligible": 1,
        "binary_success": 0,
        "double_empty": 0,
        "recall": "NA",
        "precision": "NA",
        "top1_retained": 0,
        "complete_set_success": 0,
        "rbo5_diagnostic": "NA",
        "ambiguous_matching": int(reason == "ambiguous_matching"),
        "technical_failure": 1,
        "technical_failure_reason": reason,
        "input_identity_pass": int(reason != "input_identity_mismatch"),
        "matching_started": 0,
        "strict_row_equal": "NA",
        "classifications": reason,
        "evidence_role": "fresh_concordance_promotion",
    }


def comparison_payloads(
    *,
    validation_id: str,
    pair: Sequence[Mapping[str, str]],
    receipts: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[Path, bytes]]:
    by_arm = {row["arm"]: row for row in pair}
    authority_row = by_arm["A"]
    candidate_row = by_arm["G"]
    authority_root = ROOT / authority_row["artifact_root"]
    candidate_root = ROOT / candidate_row["artifact_root"]
    authority_receipt = receipts[authority_row["attempt_id"]]
    candidate_receipt = receipts[candidate_row["attempt_id"]]
    authority_output = authority_root / str(authority_receipt["output_path"])
    candidate_output = candidate_root / str(candidate_receipt["output_path"])
    result, details = compare_candidate_topk.compare_paths(
        authority_path=authority_output,
        candidate_path=candidate_output,
        authority_receipt_path=authority_root / str(authority_receipt["input_receipt_path"]),
        candidate_receipt_path=candidate_root / str(candidate_receipt["input_receipt_path"]),
        contract_spec_path=frozen.CONTRACT_PATH,
    )
    comparison_dir = COMPARISON_ROOT / validation_id
    comparison_json = canonical_json_bytes(result)
    details_bytes = render_tsv(compare_candidate_topk.DETAIL_FIELDS, details)
    payloads = {
        comparison_dir / "comparison.json": comparison_json,
        comparison_dir / "candidate-matches.tsv": details_bytes,
        comparison_dir / "comparison.sha256": (
            f"{sha256_bytes(comparison_json)}  comparison.json\n"
            f"{sha256_bytes(details_bytes)}  candidate-matches.tsv\n"
        ).encode("ascii"),
    }
    return result, details, payloads


def exact_fraction(raw: str) -> Fraction:
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(raw), 1)


def mean_fraction(values: Sequence[str]) -> str | None:
    if not values:
        return None
    value = sum((exact_fraction(raw) for raw in values), Fraction(0, 1)) / len(values)
    with localcontext() as context:
        context.prec = 40
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
    return contract.canonical_decimal(decimal)


def build() -> dict[Path, bytes]:
    manifest, attempts, plan, _ = runner.validate_frozen_plan()
    receipts, missing_attempts = attempt_receipts(attempts)
    by_workload = {row["workload_id"]: row for row in manifest}
    by_validation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in attempts:
        by_validation[row["validation_instance_id"]].append(row)
    all_attempts_terminal = not missing_attempts and len(receipts) == len(attempts)
    comparison_allowed = all_attempts_terminal

    match_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    empty_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    rank_rows: list[dict[str, Any]] = []
    comparison_artifacts: dict[Path, bytes] = {}
    comparison_results: dict[str, dict[str, Any]] = {}
    failure_index = 0

    for row in missing_attempts:
        failure_index += 1
        failure_rows.append(
            failure_row(
                failure_id=f"failure_{failure_index:03d}",
                validation_id=row["validation_instance_id"],
                workload_id=row["workload_id"],
                repeat_id=int(row["repeat_id"]),
                primary=row["primary_instance"] == "1",
                attempt_id=row["attempt_id"],
                arm=row["arm"],
                failure_class="missing_attempt",
                reason="attempt_receipt_missing_before_fixed_budget_or_execution_stop",
                missing_output=True,
            )
        )
    for row in attempts:
        receipt = receipts.get(row["attempt_id"])
        if receipt is None or receipt["status"] == "success":
            continue
        failure_index += 1
        reason = str(receipt.get("failure_reason") or "technical_failure")
        failure_rows.append(
            failure_row(
                failure_id=f"failure_{failure_index:03d}",
                validation_id=row["validation_instance_id"],
                workload_id=row["workload_id"],
                repeat_id=int(row["repeat_id"]),
                primary=row["primary_instance"] == "1",
                attempt_id=row["attempt_id"],
                arm=row["arm"],
                failure_class="attempt_technical_failure",
                reason=reason,
                missing_output=receipt.get("output_sha256") is None,
                fallback=bool(receipt.get("fallback_used")),
            )
        )

    for validation_id, pair in sorted(by_validation.items()):
        first = pair[0]
        workload_id = first["workload_id"]
        repeat_id = int(first["repeat_id"])
        primary = first["primary_instance"] == "1"
        terminal_receipts = [receipts.get(row["attempt_id"]) for row in pair]
        pair_success = all(receipt is not None and receipt["status"] == "success" for receipt in terminal_receipts)
        result: dict[str, Any] | None = None
        details: list[dict[str, Any]] = []
        technical_reason: str | None = None
        if not comparison_allowed:
            technical_reason = "global_attempt_set_not_terminal_comparison_not_started"
        elif not pair_success:
            technical_reason = "paired_arm_technical_failure"
        else:
            try:
                result, details, artifacts = comparison_payloads(
                    validation_id=validation_id,
                    pair=pair,
                    receipts=receipts,
                )
                comparison_artifacts.update(artifacts)
                comparison_results[validation_id] = result
                if result["technical_failure"]:
                    technical_reason = str(result["technical_failure_reason"])
                    failure_index += 1
                    failure_rows.append(
                        failure_row(
                            failure_id=f"failure_{failure_index:03d}",
                            validation_id=validation_id,
                            workload_id=workload_id,
                            repeat_id=repeat_id,
                            primary=primary,
                            attempt_id="offline_comparator",
                            arm="A/G",
                            failure_class="comparator_technical_failure",
                            reason=technical_reason,
                            input_mismatch=technical_reason == "input_identity_mismatch",
                            ambiguous=technical_reason == "ambiguous_matching",
                        )
                    )
            except Exception as error:  # A malformed comparator input is retained as failure.
                technical_reason = f"comparator_exception:{type(error).__name__}:{error}"
                failure_index += 1
                failure_rows.append(
                    failure_row(
                        failure_id=f"failure_{failure_index:03d}",
                        validation_id=validation_id,
                        workload_id=workload_id,
                        repeat_id=repeat_id,
                        primary=primary,
                        attempt_id="offline_comparator",
                        arm="A/G",
                        failure_class="comparator_exception",
                        reason=technical_reason,
                    )
                )

        if result is None or technical_reason is not None:
            reason = technical_reason or "technical_failure"
            metric_rows.extend(
                technical_metric(
                    validation_id=validation_id,
                    workload_id=workload_id,
                    repeat_id=repeat_id,
                    primary=primary,
                    mode=mode,
                    reason=reason,
                )
                for mode in contract.RANKING_MODES
            )
            continue

        for detail in details:
            match_rows.append(
                {
                    "validation_instance_id": validation_id,
                    "repeat_id": repeat_id,
                    "primary_instance": primary,
                    **{field: detail.get(field, "NA") for field in compare_candidate_topk.DETAIL_FIELDS},
                }
            )
        for mode in contract.RANKING_MODES:
            value = result["modes"][mode]
            metric_rows.append(
                {
                    "validation_instance_id": validation_id,
                    "workload_id": workload_id,
                    "repeat_id": repeat_id,
                    "primary_instance": primary,
                    "ranking_mode": mode,
                    "comparison_status": result["comparison_status"],
                    "reference_candidate_count": value["reference_candidate_count"],
                    "candidate_candidate_count": value["candidate_candidate_count"],
                    "matched_count": value["matched_count"],
                    "informative_for_recovery": value["informative_for_recovery"],
                    "binary_gate_denominator_eligible": value["binary_gate_denominator_eligible"],
                    "binary_success": value["binary_success"],
                    "double_empty": value["double_empty"],
                    "recall": value["recall"],
                    "precision": value["precision"],
                    "top1_retained": value["top1_retained"],
                    "complete_set_success": value["binary_success"],
                    "rbo5_diagnostic": value["rank_diagnostic"]["finite_rbo_fraction"],
                    "ambiguous_matching": value["ambiguous_matching"],
                    "technical_failure": False,
                    "technical_failure_reason": None,
                    "input_identity_pass": result["input_identity_pass"],
                    "matching_started": result["matching_started"],
                    "strict_row_equal": value["strict_row_equal"],
                    "classifications": ";".join(value["classifications"]) or "none",
                    "evidence_role": "fresh_concordance_promotion",
                }
            )
            diagnostic = value["rank_diagnostic"]
            rank_rows.append(
                {
                    "validation_instance_id": validation_id,
                    "workload_id": workload_id,
                    "repeat_id": repeat_id,
                    "primary_instance": primary,
                    "ranking_mode": mode,
                    "depth": diagnostic["depth"],
                    "persistence": diagnostic["persistence"],
                    "finite_rbo_fraction": diagnostic["finite_rbo_fraction"],
                    "finite_rbo_decimal": diagnostic["finite_rbo_decimal"],
                    "rank_displacements_json": diagnostic["rank_displacements"],
                    "claim_role": "diagnostic_only",
                }
            )
        if result["clean_double_empty"]:
            score = result["modes"]["score"]
            empty_rows.append(
                {
                    "validation_instance_id": validation_id,
                    "workload_id": workload_id,
                    "repeat_id": repeat_id,
                    "primary_instance": primary,
                    "authority_candidate_count_score": score["reference_candidate_count"],
                    "candidate_candidate_count_score": score["candidate_candidate_count"],
                    "clean_double_empty_all_modes": True,
                    "binary_gate_denominator_eligible": False,
                    "evidence_role": "fresh_concordance_promotion",
                }
            )

    metric_rows.sort(key=lambda row: (row["workload_id"], int(row["repeat_id"]), contract.RANKING_MODES.index(row["ranking_mode"])))
    primary_metrics = [row for row in metric_rows if row["primary_instance"] in {True, 1}]
    require(len(primary_metrics) == 178 * 3, "primary workload metric representation drift")
    endpoint_specs = (
        (1, "score_complete_set_success", "score", "binary_success"),
        (2, "stability_complete_set_success", "stability", "binary_success"),
        (3, "nt_complete_set_success", "nt", "binary_success"),
        (4, "score_top1_retention", "score", "top1_retained"),
        (5, "stability_top1_retention", "stability", "top1_retained"),
        (6, "nt_top1_retention", "nt", "top1_retained"),
    )
    bound_rows: list[dict[str, Any]] = []
    fixed_sequence_reached = True
    for order, endpoint, mode, field in endpoint_specs:
        rows = [row for row in primary_metrics if row["ranking_mode"] == mode]
        bound = exact_binomial_bounds.endpoint_bounds(rows, endpoint_field=field)
        threshold_pass = bool(bound["threshold_pass"])
        bound_rows.append(
            {
                "endpoint_order": order,
                "endpoint_name": endpoint,
                "ranking_mode": mode,
                **{key: bound[key] for key in (
                    "successes", "trials", "estimate", "alpha_one_sided",
                    "lower_confidence_bound", "promotion_threshold", "threshold_pass", "method",
                )},
                "fixed_sequence_gate_reached": fixed_sequence_reached,
            }
        )
        fixed_sequence_reached = fixed_sequence_reached and threshold_pass

    primary_score = [row for row in primary_metrics if row["ranking_mode"] == "score"]
    denominator_count = sum(row["binary_gate_denominator_eligible"] in {True, 1, "1"} for row in primary_score)
    informative_count = sum(row["informative_for_recovery"] in {True, 1, "1"} for row in primary_score)
    reference_sites = sum(
        int(row["reference_candidate_count"])
        for row in primary_score
        if row["informative_for_recovery"] in {True, 1, "1"}
    )
    technical_failure_count = sum(receipt["status"] != "success" for receipt in receipts.values()) + len(missing_attempts)
    missing_output_count = sum(row["missing_output"] in {True, 1} for row in failure_rows)
    input_mismatch_count = sum(row["input_identity_mismatch"] in {True, 1} for row in failure_rows)
    ambiguous_count = sum(row["ambiguous_matching"] in {True, 1} for row in failure_rows)
    fallback_count = sum(row["unexpected_fallback"] in {True, 1} for row in failure_rows)
    sample_size = load_json(frozen.SAMPLE_SIZE_PATH)
    information_gate = (
        denominator_count >= int(sample_size["n_binary_required"])
        and informative_count >= 60
        and reference_sites >= 240
    )
    endpoint_gate = all(row["threshold_pass"] for row in bound_rows)
    technical_gate = all(value == 0 for value in (
        technical_failure_count, missing_output_count, input_mismatch_count, ambiguous_count, fallback_count,
    ))
    uniqueness_gate = (
        len({row["query_sequence_sha256"] for row in manifest}) == 178
        and len({(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in manifest}) == 178
        and len({row["target_sequence_sha256"] for row in manifest}) == 178
        and len({(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in manifest}) == 178
    )
    if not information_gate:
        status = "blocked_insufficient_information"
    elif endpoint_gate and technical_gate and uniqueness_gate:
        status = "pass"
    else:
        status = "no_go"

    matches_bytes = render_tsv(MATCH_FIELDS, match_rows)
    metrics_bytes = render_tsv(WORKLOAD_FIELDS, metric_rows)
    empty_bytes = render_tsv(EMPTY_FIELDS, empty_rows)
    failure_bytes = render_tsv(FAILURE_FIELDS, failure_rows)
    bounds_bytes = render_tsv(BOUND_FIELDS, bound_rows)
    rank_bytes = render_tsv(RANK_FIELDS, rank_rows)
    tracked_source_payloads = {
        MATCHES_PATH: matches_bytes,
        WORKLOAD_METRICS_PATH: metrics_bytes,
        EMPTY_PATH: empty_bytes,
        FAILURE_PATH: failure_bytes,
        BOUNDS_PATH: bounds_bytes,
        RANK_PATH: rank_bytes,
    }
    primary_recall = [str(row["recall"]) for row in primary_metrics if row["ranking_mode"] == "score" and row["recall"] not in {None, "NA"}]
    primary_precision = [str(row["precision"]) for row in primary_metrics if row["ranking_mode"] == "score" and row["precision"] not in {None, "NA"}]
    receipt = {
        "schema_version": 1,
        "phase": 4,
        "status": "complete" if all_attempts_terminal else "fixed_budget_or_execution_stop_with_missing_attempts",
        "evidence_role": "fresh_concordance_promotion",
        "manifest_sha256": sha256_file(frozen.MANIFEST_PATH),
        "attempt_plan_sha256": sha256_file(frozen.ATTEMPT_PLAN_PATH),
        "source_commit": next(iter({str(receipt["source_commit"]) for receipt in receipts.values()}), None),
        "planned_primary_workloads": 178,
        "planned_validation_instances": 184,
        "planned_attempts": 368,
        "terminal_attempts": len(receipts),
        "successful_attempts": sum(receipt["status"] == "success" for receipt in receipts.values()),
        "comparison_global_start_gate": "all_attempts_terminal",
        "comparison_global_start_gate_pass": comparison_allowed,
        "comparison_count": len(comparison_results),
        "primary_metric_count": len(primary_metrics),
        "technical_repeat_metric_count": len(metric_rows) - len(primary_metrics),
        "double_empty_primary_workload_count": sum(row["primary_instance"] in {True, 1} for row in empty_rows),
        "descriptive_score_macro_recall": mean_fraction(primary_recall),
        "descriptive_score_macro_precision": mean_fraction(primary_precision),
        "source_data_sha256": {path.relative_to(ROOT).as_posix(): sha256_bytes(payload) for path, payload in tracked_source_payloads.items()},
        "attempt_receipt_sha256": {
            attempt_id: sha256_file(ROOT / next(row["artifact_root"] for row in attempts if row["attempt_id"] == attempt_id) / "attempt-complete.json")
            for attempt_id in sorted(receipts)
        },
        "comparison_artifact_sha256": {path.relative_to(ROOT).as_posix(): sha256_bytes(payload) for path, payload in comparison_artifacts.items()},
        "no_retries_or_replacements": all(not receipt["replacement_retry_allowed"] for receipt in receipts.values()),
        "technical_repeats_excluded_from_independent_n": True,
        "rank_order_claim": "diagnostic_only",
    }
    receipt_bytes = canonical_json_bytes(receipt)
    decision = {
        "schema_version": 1,
        "phase": 4,
        "decision": status,
        "contract_name": "biological_topk_candidate_site_v1",
        "claim_scope": "set_preservation_with_top1_retention",
        "rank_order_claim": "diagnostic_only",
        "primary_workload_count": 178,
        "binary_gate_denominator_count": denominator_count,
        "n_binary_required": int(sample_size["n_binary_required"]),
        "informative_reference_nonempty_workload_count": informative_count,
        "minimum_informative_reference_nonempty_workloads": 60,
        "total_reference_candidate_sites": reference_sites,
        "minimum_total_reference_candidate_sites": 240,
        "information_gate_pass": information_gate,
        "endpoint_gate_pass": endpoint_gate,
        "exact_binomial_bounds_sha256": sha256_bytes(bounds_bytes),
        "technical_failure_count": technical_failure_count,
        "missing_output_count": missing_output_count,
        "input_identity_mismatch_count": input_mismatch_count,
        "ambiguous_matching_count": ambiguous_count,
        "unexpected_fallback_count": fallback_count,
        "zero_technical_failure_gate_pass": technical_gate,
        "primary_identity_uniqueness_gate_pass": uniqueness_gate,
        "all_promotion_gates_pass": status == "pass",
        "contract_status_if_applied": (
            "fresh_concordance_pass" if status == "pass"
            else "concordance_no_go" if status == "no_go"
            else "in_validation"
        ),
        "gpu_screen_status_if_applied": "experimental",
        "bioinformatics_route_if_applied": (
            "conditionally_reopened" if status in {"pass", "blocked_insufficient_information"}
            else "closed_for_this_contract"
        ),
        "fresh_holdout_receipt_sha256": sha256_bytes(receipt_bytes),
        "no_post_run_supplementation": True,
    }
    payloads = {
        **comparison_artifacts,
        **tracked_source_payloads,
        RECEIPT_PATH: receipt_bytes,
        DECISION_PATH: canonical_json_bytes(decision),
    }
    return payloads


def preflight() -> dict[str, Any]:
    manifest, attempts, plan, _ = runner.validate_frozen_plan()
    tracked_outputs = (
        MATCHES_PATH, WORKLOAD_METRICS_PATH, EMPTY_PATH, FAILURE_PATH,
        BOUNDS_PATH, RANK_PATH, RECEIPT_PATH, DECISION_PATH,
    )
    return {
        "schema_version": 1,
        "status": "preflight_pass",
        "read_only": True,
        "scientific_output_created": False,
        "primary_workload_count": len(manifest),
        "validation_instance_count": len({row["validation_instance_id"] for row in attempts}),
        "attempt_count": len(attempts),
        "comparison_policy": "offline_after_all_attempts_terminal",
        "exact_analysis_command": plan["exact_analysis_command"],
        "tracked_scientific_outputs_currently_present": sum(path.exists() for path in tracked_outputs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--analyze", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--artifact-root", type=Path, default=ARTIFACT_ROOT)
    args = parser.parse_args()
    try:
        require(args.artifact_root.resolve() == ARTIFACT_ROOT.resolve(), "artifact root differs from the frozen path")
        if args.preflight:
            print(json.dumps(preflight(), indent=2, sort_keys=True, allow_nan=False))
            return 0
        payloads = build()
        if args.check:
            stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
            if stale:
                parser.exit(1, "stale fresh holdout analysis artifacts: " + ", ".join(stale) + "\n")
            print("biological Top-K fresh holdout analysis reproduces byte-for-byte")
            return 0
        for path, payload in payloads.items():
            atomic_write(path, payload)
        print(f"wrote {len(payloads)} fresh holdout analysis artifacts")
        return 0
    except (
        AnalysisError,
        runner.RunnerError,
        frozen.FreezeError,
        contract.ContractError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(f"biological Top-K fresh holdout analysis failed: {error}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("_")]
