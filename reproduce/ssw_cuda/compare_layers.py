#!/usr/bin/env python3
"""Compare authority and candidate SSW evidence at frozen layers L0-L8."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1"
CIGAR_RE = re.compile(r"([1-9][0-9]*)([MID])")
TOP5_KEYS = ("score", "stability", "Nt")


class ComparisonError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ComparisonError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    require(isinstance(value, list), f"{label} must be an array")
    return value


def validate_bundle(bundle: Any, label: str) -> dict[str, Any]:
    value = require_mapping(bundle, label)
    require(value.get("schema_version") == SCHEMA_VERSION, f"{label} schema drift")
    require(isinstance(value.get("case_id"), str) and value["case_id"], f"{label} case_id missing")
    prealign = require_mapping(value.get("prealign"), f"{label}.prealign")
    alignment = require_mapping(value.get("alignment"), f"{label}.alignment")
    require(prealign.get("record_kind") == "prealign", f"{label} prealign kind drift")
    require(alignment.get("record_kind") == "alignment", f"{label} alignment kind drift")
    require_list(prealign.get("dp_passes"), f"{label}.prealign.dp_passes")
    require_mapping(prealign.get("selection"), f"{label}.prealign.selection")
    require_list(alignment.get("dp_passes"), f"{label}.alignment.dp_passes")
    require_mapping(alignment.get("forward_endpoint"), f"{label}.alignment.forward_endpoint")
    require_mapping(alignment.get("reverse_start"), f"{label}.alignment.reverse_start")
    traceback = require_mapping(alignment.get("traceback"), f"{label}.alignment.traceback")
    parse_cigar(traceback.get("cigar"), f"{label}.alignment.traceback.cigar")
    require_list(alignment.get("emitted_rows"), f"{label}.alignment.emitted_rows")
    top5 = require_mapping(value.get("clustered_top5"), f"{label}.clustered_top5")
    for key in TOP5_KEYS:
        rows = require_list(top5.get(key), f"{label}.clustered_top5.{key}")
        require(len(rows) <= 5, f"{label}.clustered_top5.{key} exceeds Top 5")
    require_list(value.get("full_output_row_digests"), f"{label}.full_output_row_digests")
    return value


def parse_cigar(value: Any, label: str = "cigar") -> list[dict[str, Any]]:
    require(isinstance(value, str) and value, f"{label} must be a nonempty string")
    operations = [
        {"length": int(length), "operation": operation}
        for length, operation in CIGAR_RE.findall(value)
    ]
    require(
        "".join(f"{item['length']}{item['operation']}" for item in operations) == value,
        f"invalid {label}: {value}",
    )
    return operations


def first_list_difference(authority: list[Any], candidate: list[Any]) -> int | None:
    for index, (left, right) in enumerate(zip(authority, candidate)):
        if left != right:
            return index
    if len(authority) != len(candidate):
        return min(len(authority), len(candidate))
    return None


def final_prealign_pass(record: dict[str, Any], label: str) -> dict[str, Any]:
    numeric_path = record.get("final_numeric_path")
    passes = [
        item
        for item in require_list(record.get("dp_passes"), f"{label}.dp_passes")
        if isinstance(item, dict)
        and item.get("stage") == "prealign"
        and item.get("numeric_path") == numeric_path
    ]
    require(len(passes) == 1, f"{label} must contain one final prealign pass")
    selected = passes[0]
    require_list(selected.get("columns"), f"{label}.final.columns")
    require(
        selected.get("column_count") == len(selected["columns"]),
        f"{label} column_count drift",
    )
    return selected


def selection_items(selection: dict[str, Any], label: str) -> list[dict[str, Any]]:
    rows = require_list(selection.get("scoreinfos"), f"{label}.scoreinfos")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        item = require_mapping(row, f"{label}.scoreinfos[{index}]")
        require(
            set(item) == {"index", "position", "score"},
            f"{label}.scoreinfos[{index}] fields drift",
        )
        normalized.append({key: item[key] for key in ("index", "position", "score")})
    return normalized


def multiset_difference(left: Iterable[Any], right: Iterable[Any]) -> list[Any]:
    left_values = list(left)
    right_counts = Counter(canonical(value) for value in right)
    result: list[Any] = []
    for value in left_values:
        key = canonical(value)
        if right_counts[key]:
            right_counts[key] -= 1
        else:
            result.append(value)
    return result


def compare_layers(authority_bundle: Any, candidate_bundle: Any) -> dict[str, Any]:
    authority = validate_bundle(authority_bundle, "authority")
    candidate = validate_bundle(candidate_bundle, "candidate")
    require(authority["case_id"] == candidate["case_id"], "case_id mismatch")

    authority_prealign = authority["prealign"]
    candidate_prealign = candidate["prealign"]
    authority_alignment = authority["alignment"]
    candidate_alignment = candidate["alignment"]

    l0_fields = ("input", "scoring", "workload")
    l0_prealign_equal = all(
        authority_prealign.get(field) == candidate_prealign.get(field) for field in l0_fields
    )
    l0_alignment_equal = all(
        authority_alignment.get(field) == candidate_alignment.get(field) for field in l0_fields
    )
    l0_equal = l0_prealign_equal and l0_alignment_equal

    authority_pass = final_prealign_pass(authority_prealign, "authority.prealign")
    candidate_pass = final_prealign_pass(candidate_prealign, "candidate.prealign")
    authority_columns = authority_pass["columns"]
    candidate_columns = candidate_pass["columns"]
    first_diff_column = first_list_difference(authority_columns, candidate_columns)
    l1_metadata_fields = (
        "numeric_path",
        "ref_direction",
        "column_count",
        "column_max_digest_fnv1a64",
        "maximum_score",
    )
    l1_equal = first_diff_column is None and all(
        authority_pass.get(field) == candidate_pass.get(field) for field in l1_metadata_fields
    )

    authority_selection = authority_prealign["selection"]
    candidate_selection = candidate_prealign["selection"]
    authority_items = selection_items(authority_selection, "authority.prealign.selection")
    candidate_items = selection_items(candidate_selection, "candidate.prealign.selection")
    false_negative = multiset_difference(authority_items, candidate_items)
    extra = multiset_difference(candidate_items, authority_items)
    order_equal = authority_items == candidate_items
    l2_policy_fields = (
        "threshold",
        "threshold_predicate",
        "adjacent_distance_exclusive_upper_bound",
        "equal_score_tie",
    )
    l2_equal = order_equal and all(
        authority_selection.get(field) == candidate_selection.get(field)
        for field in l2_policy_fields
    )

    l3_equal = authority_alignment["forward_endpoint"] == candidate_alignment["forward_endpoint"]
    l4_equal = authority_alignment["reverse_start"] == candidate_alignment["reverse_start"]

    authority_cigar = authority_alignment["traceback"]["cigar"]
    candidate_cigar = candidate_alignment["traceback"]["cigar"]
    authority_operations = parse_cigar(authority_cigar, "authority cigar")
    candidate_operations = parse_cigar(candidate_cigar, "candidate cigar")
    first_diff_op = first_list_difference(authority_operations, candidate_operations)
    l5_cigar_equal = first_diff_op is None
    l5_band_equal = authority_alignment.get("band_history") == candidate_alignment.get("band_history")
    l5_equal = l5_cigar_equal and l5_band_equal

    l6_equal = authority_alignment["emitted_rows"] == candidate_alignment["emitted_rows"]

    l7_equal = {
        key: authority["clustered_top5"][key] == candidate["clustered_top5"][key]
        for key in TOP5_KEYS
    }
    l7_all_equal = all(l7_equal.values())
    l8_equal = authority["full_output_row_digests"] == candidate["full_output_row_digests"]

    layer_equal = {
        "L0": l0_equal,
        "L1": l1_equal,
        "L2": l2_equal,
        "L3": l3_equal,
        "L4": l4_equal,
        "L5": l5_equal,
        "L6": l6_equal,
        "L7": l7_all_equal,
        "L8": l8_equal,
    }
    first_divergent_layer = next(
        (layer for layer in (f"L{index}" for index in range(9)) if not layer_equal[layer]),
        None,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": authority["case_id"],
        "L0_input_equal": l0_equal,
        "L0_prealign_equal": l0_prealign_equal,
        "L0_alignment_equal": l0_alignment_equal,
        "L1_column_equal": l1_equal,
        "L1_first_diff_column": first_diff_column,
        "L2_selection_equal": l2_equal,
        "L2_false_negative": false_negative,
        "L2_extra": extra,
        "L2_order_equal": order_equal,
        "L3_forward_equal": l3_equal,
        "L4_reverse_equal": l4_equal,
        "L5_cigar_equal": l5_cigar_equal,
        "L5_band_history_equal": l5_band_equal,
        "L5_first_diff_op": first_diff_op,
        "L6_row_equal": l6_equal,
        "L7_score_top5_equal": l7_equal["score"],
        "L7_stability_top5_equal": l7_equal["stability"],
        "L7_Nt_top5_equal": l7_equal["Nt"],
        "L7_score_stability_Nt_top5_equal": l7_all_equal,
        "L8_full_output_diagnostic_equal": l8_equal,
        "L8_contract_status": "diagnostic_only",
        "first_divergent_layer": first_divergent_layer,
    }


def read_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("authority", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = compare_layers(read_json(arguments.authority), read_json(arguments.candidate))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        require(not arguments.output.is_symlink(), f"unsafe output path: {arguments.output}")
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ComparisonError as error:
        print(f"layer comparison error: {error}", file=sys.stderr)
        raise SystemExit(1)
