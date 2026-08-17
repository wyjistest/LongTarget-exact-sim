#!/usr/bin/env python3
"""Consolidate the input-only Phase 1 feasibility and sample-size plans."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
CONTRACT_PATH = ROOT / "reproduce/biological_topk/contract.py"
FEASIBILITY_PATH = PAPER / "fresh_information_feasibility.json"
SAMPLE_SIZE_PATH = PAPER / "sample_size_plan.json"

POWER_PATH = PAPER / "concordance_power_plan.json"
JOINT_MODEL_PATH = PAPER / "joint_information_model.json"
JOINT_SIMULATION_PATH = PAPER / "joint_information_simulation.json"
SOURCE_RECEIPT_PATH = PAPER / "source_universe_receipt.json"
RESOURCE_MODEL_PATH = PAPER / "resource_projection_model.json"
RESOURCE_RECEIPT_PATH = PAPER / "resource_projection_model_receipt.json"
BUDGET_PATH = PAPER / "fresh_budget_projection_plan.json"

EXPECTED_QUOTAS = {"short": 60, "medium": 59, "large": 59}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_contract():
    spec = importlib.util.spec_from_file_location(
        "biological_topk_feasibility_contract", CONTRACT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CONTRACT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(payload, dict), f"expected JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii")


def resource_projection(model: dict[str, Any]) -> dict[str, dict[str, str]]:
    projection = model["projection"]
    return {
        "cpu_aggregate_wall_seconds": {
            "point": projection["projected_cpu_aggregate_wall_seconds_point"],
            "upper_95": projection["projected_cpu_aggregate_wall_seconds_upper_95"],
        },
        "gpu_aggregate_wall_seconds": {
            "point": projection["projected_gpu_aggregate_wall_seconds_point"],
            "upper_95": projection["projected_gpu_aggregate_wall_seconds_upper_95"],
        },
        "gpu_hours": {
            "point": projection["projected_gpu_hours_point"],
            "upper_95": projection["projected_gpu_hours_upper_95"],
        },
        "scheduled_elapsed_wall_seconds": {
            "point": projection["projected_scheduled_elapsed_wall_seconds_point"],
            "upper_95": projection["projected_scheduled_elapsed_wall_seconds_upper_95"],
        },
        "artifact_storage_bytes": {
            "point": projection["projected_artifact_storage_bytes_point"],
            "upper_95": projection["projected_artifact_storage_bytes_upper_95"],
        },
    }


def build() -> dict[Path, bytes]:
    contract = load_contract()
    power = load_json(POWER_PATH)
    joint_model = load_json(JOINT_MODEL_PATH)
    joint = load_json(JOINT_SIMULATION_PATH)
    source = load_json(SOURCE_RECEIPT_PATH)
    resource = load_json(RESOURCE_MODEL_PATH)
    resource_receipt = load_json(RESOURCE_RECEIPT_PATH)
    budget = load_json(BUDGET_PATH)

    n_required, k_min, achieved_power = contract.required_binary_n()
    panel_n, eligibility_tail = contract.required_panel_n(n_required)
    previous_tail = contract.binomial_tail(panel_n - 1, n_required, "0.75")
    require((n_required, k_min) == (124, 122), "exact-binomial boundary drift")
    require(panel_n == 178, "default panel-size boundary drift")
    require(power["n_binary_required"] == n_required, "power-plan n drift")
    require(power["k_min"] == k_min, "power-plan k_min drift")
    require(Decimal(power["achieved_power"]) == achieved_power, "power-plan power drift")
    require(
        Decimal(power["default_panel_eligibility_probability"]) == eligibility_tail,
        "eligibility-tail fixture drift",
    )

    require(joint["N_panel"] == panel_n, "joint simulation panel size drift")
    require(joint["stratum_quotas"] == EXPECTED_QUOTAS, "joint quotas drift")
    require(sum(EXPECTED_QUOTAS.values()) == panel_n, "quota total drift")
    require(joint["joint_information_gate_pass"] is True, "joint information gate failed")
    require(joint["joint_inner_mc_precision_pass"] is True, "joint MC precision failed")
    require(
        Decimal(joint["joint_information_probability_lcb"])
        >= Decimal(joint["joint_information_gate_threshold"]),
        "joint information LCB is below threshold",
    )
    require(
        joint["inner_simulations_are_independent_scientific_evidence"] is False,
        "inner simulations were misclassified as scientific evidence",
    )

    query_capacity = source["query_universe"]
    query_capacity_pass = (
        query_capacity["fresh_unique_sequence_digest_count"] >= panel_n
        and query_capacity["fresh_unique_namespaced_ordinal_count"] >= panel_n
    )
    target_capacity: dict[str, dict[str, Any]] = {}
    for stratum, quota in EXPECTED_QUOTAS.items():
        observed = source["target_universe"]["strata"][stratum]
        target_capacity[stratum] = {
            "required": quota,
            "fresh_unique_sequence_digest_count": observed[
                "fresh_unique_sequence_digest_count"
            ],
            "fresh_unique_namespaced_ordinal_count": observed[
                "fresh_unique_namespaced_ordinal_count"
            ],
            "gate_pass": (
                observed["fresh_unique_sequence_digest_count"] >= quota
                and observed["fresh_unique_namespaced_ordinal_count"] >= quota
            ),
        }
    target_capacity_pass = all(row["gate_pass"] for row in target_capacity.values())
    source_capacity_pass = query_capacity_pass and target_capacity_pass

    model_sha = sha256_file(RESOURCE_MODEL_PATH)
    require(resource_receipt["model_sha256"] == model_sha, "resource receipt digest drift")
    require(budget["model_sha256"] == model_sha, "budget model digest drift")
    require(resource["stratum_quotas"] == EXPECTED_QUOTAS, "resource quotas drift")
    require(budget["N_panel"] == panel_n, "budget panel size drift")
    elapsed_pass = budget["scheduled_wall_gate_pass"] is True
    gpu_pass = budget["gpu_hours_gate_pass"] is True
    storage_quota = budget["max_artifact_storage_bytes"]
    require(
        storage_quota is None
        or (isinstance(storage_quota, int) and not isinstance(storage_quota, bool) and storage_quota > 0),
        "storage quota must be null or a positive integer",
    )
    storage_upper = int(resource["projection"]["projected_artifact_storage_bytes_upper_95"])
    storage_pass = None if storage_quota is None else storage_upper <= storage_quota
    require(
        budget["artifact_storage_gate_pass"] == storage_pass,
        "budget storage-gate result drift",
    )
    fixed_budget_pass = (
        None if storage_pass is None else elapsed_pass and gpu_pass and storage_pass
    )
    require(budget["fixed_budget_gate_pass"] == fixed_budget_pass, "fixed-budget result drift")

    power_pass = achieved_power >= Decimal(power["minimum_primary_gate_power"])
    eligibility_pass = eligibility_tail >= Decimal(power["eligibility_probability_target"])
    joint_pass = joint["joint_information_gate_pass"] is True
    all_computable_gates_pass = all(
        (power_pass, eligibility_pass, joint_pass, source_capacity_pass, elapsed_pass, gpu_pass)
    )
    if not power_pass or not eligibility_pass or not joint_pass:
        recommended_status = "blocked_insufficient_information"
        blocking_reason = "statistical_or_joint_information_gate_failed"
    elif not source_capacity_pass:
        recommended_status = "blocked_insufficient_source_universe"
        blocking_reason = "fresh_unique_query_or_target_capacity_failed"
    elif not elapsed_pass or not gpu_pass:
        recommended_status = "blocked_fixed_budget"
        blocking_reason = "elapsed_or_gpu_budget_failed"
    elif storage_quota is None:
        recommended_status = "blocked_fixed_budget"
        blocking_reason = "owner_storage_quota_missing"
    elif storage_pass is not True:
        recommended_status = "blocked_fixed_budget"
        blocking_reason = "projected_storage_exceeds_owner_quota"
    else:
        recommended_status = "pass"
        blocking_reason = None

    plan_status = (
        "frozen"
        if recommended_status == "pass"
        else f"{recommended_status}_{blocking_reason}"
    )
    panel_selection_status = (
        "frozen_minimum_satisfying_all_gates"
        if recommended_status == "pass"
        else "provisional_statistical_minimum_not_authorized_for_selection"
    )
    projected_resources = resource_projection(resource)
    artifact_digests = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in (
            POWER_PATH,
            JOINT_MODEL_PATH,
            JOINT_SIMULATION_PATH,
            SOURCE_RECEIPT_PATH,
            RESOURCE_MODEL_PATH,
            RESOURCE_RECEIPT_PATH,
            BUDGET_PATH,
        )
    }

    feasibility = {
        "schema_version": 1,
        "status": plan_status,
        "phase_1_status_recommendation": recommended_status,
        "blocking_reason": blocking_reason,
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "candidate_N_panel": panel_n,
        "panel_selection_status": panel_selection_status,
        "stratum_quotas": EXPECTED_QUOTAS,
        "minimality": {
            "n_binary_required": n_required,
            "N_panel_minus_one": panel_n - 1,
            "N_panel_minus_one_eligibility_tail_probability": contract.canonical_decimal(
                previous_tail
            ),
            "N_panel": panel_n,
            "N_panel_eligibility_tail_probability": contract.canonical_decimal(
                eligibility_tail
            ),
            "eligibility_tail_target": power["eligibility_probability_target"],
            "minimal_statistical_panel_pass": (
                previous_tail < Decimal(power["eligibility_probability_target"])
                <= eligibility_tail
            ),
        },
        "information": {
            "p_binary_denominator_eligible_planning": power[
                "p_binary_denominator_eligible_planning"
            ],
            "p_reference_nonempty_planning": joint_model[
                "p_reference_nonempty_planning"
            ],
            "reference_candidate_count_distribution_planning": joint_model[
                "candidate_count_distributions"
            ],
            "marginal_probability_point": joint["marginal_probability_point"],
            "marginal_probability_outer_lcb": joint[
                "marginal_probability_outer_lcb"
            ],
            "joint_information_probability_point": joint[
                "joint_information_probability_point"
            ],
            "joint_information_probability_lcb": joint[
                "joint_information_probability_lcb"
            ],
            "joint_inner_mc_precision_pass": joint[
                "joint_inner_mc_precision_pass"
            ],
        },
        "source_capacity": {
            "query": {
                "required": panel_n,
                "fresh_unique_sequence_digest_count": query_capacity[
                    "fresh_unique_sequence_digest_count"
                ],
                "fresh_unique_namespaced_ordinal_count": query_capacity[
                    "fresh_unique_namespaced_ordinal_count"
                ],
                "gate_pass": query_capacity_pass,
            },
            "targets_by_stratum": target_capacity,
            "gate_pass": source_capacity_pass,
        },
        "resource": {
            "projection_model_sha256": model_sha,
            "projected": projected_resources,
            "max_formal_scheduled_wall_seconds": budget[
                "max_formal_scheduled_wall_seconds"
            ],
            "max_gpu_hours": budget["max_gpu_hours"],
            "max_artifact_storage_bytes": storage_quota,
            "scheduled_wall_gate_pass": elapsed_pass,
            "gpu_hours_gate_pass": gpu_pass,
            "artifact_storage_gate_pass": storage_pass,
            "fixed_budget_gate_pass": fixed_budget_pass,
        },
        "gates": {
            "exact_binomial_power_pass": power_pass,
            "denominator_eligibility_probability_pass": eligibility_pass,
            "joint_information_probability_pass": joint_pass,
            "source_universe_capacity_pass": source_capacity_pass,
            "scheduled_wall_budget_pass": elapsed_pass,
            "gpu_hours_budget_pass": gpu_pass,
            "artifact_storage_budget_pass": storage_pass,
            "all_computable_gates_pass": all_computable_gates_pass,
            "all_required_gates_pass": fixed_budget_pass is True and all_computable_gates_pass,
        },
        "artifact_sha256": artifact_digests,
    }

    sample_size = {
        "schema_version": 1,
        "status": plan_status,
        "phase_1_status_recommendation": recommended_status,
        "blocking_reason": blocking_reason,
        "primary_alternative_p": power["p_alt"],
        "power_target": power["minimum_primary_gate_power"],
        "n_binary_required": n_required,
        "k_min": k_min,
        "allowed_failures": n_required - k_min,
        "achieved_power": contract.canonical_decimal(achieved_power),
        "p_binary_denominator_eligible_planning": power[
            "p_binary_denominator_eligible_planning"
        ],
        "eligibility_probability_target": power["eligibility_probability_target"],
        "N_panel": panel_n,
        "N_panel_selection_status": panel_selection_status,
        "stratum_quotas": EXPECTED_QUOTAS,
        "probability_eligible_count_ge_n_binary_required": contract.canonical_decimal(
            eligibility_tail
        ),
        "p_reference_nonempty_planning": joint_model["p_reference_nonempty_planning"],
        "reference_candidate_count_distribution_planning": joint_model[
            "candidate_count_distributions"
        ],
        "probability_reference_nonempty_count_ge_60": joint[
            "marginal_probability_point"
        ]["reference_nonempty_count"],
        "probability_total_reference_candidate_sites_ge_240": joint[
            "marginal_probability_point"
        ]["total_reference_candidate_sites"],
        "joint_model_marginal_probability_point": joint[
            "marginal_probability_point"
        ],
        "joint_model_marginal_probability_outer_lcb": joint[
            "marginal_probability_outer_lcb"
        ],
        "joint_information_probability_point": joint[
            "joint_information_probability_point"
        ],
        "joint_information_probability_lcb": joint[
            "joint_information_probability_lcb"
        ],
        "joint_outer_bootstrap_replicates": joint[
            "joint_outer_bootstrap_replicates"
        ],
        "joint_outer_lcb_quantile": joint["joint_outer_lcb_quantile"],
        "joint_inner_simulations_min": joint[
            "joint_inner_panel_simulations_initial"
        ],
        "joint_inner_simulations_max": joint["joint_inner_panel_simulations_max"],
        "joint_inner_simulations_actual_distribution": joint[
            "inner_simulation_count_distribution"
        ],
        "joint_inner_mc_halfwidth_max": joint["joint_inner_mc_halfwidth_max"],
        "joint_inner_mc_halfwidth_max_observed": joint[
            "inner_mc_halfwidth_max_observed"
        ],
        "joint_inner_mc_precision_pass": joint["joint_inner_mc_precision_pass"],
        "resource_projection_model_sha256": model_sha,
        "projected_resources": projected_resources,
        "resource_limits": {
            "max_formal_scheduled_wall_seconds": budget[
                "max_formal_scheduled_wall_seconds"
            ],
            "max_gpu_hours": budget["max_gpu_hours"],
            "max_artifact_storage_bytes": storage_quota,
        },
        "resource_gates": {
            "scheduled_wall_gate_pass": elapsed_pass,
            "gpu_hours_gate_pass": gpu_pass,
            "artifact_storage_gate_pass": storage_pass,
            "fixed_budget_gate_pass": fixed_budget_pass,
        },
        "source_capacity_gate_pass": source_capacity_pass,
        "secondary_marginal_powers": power["secondary_marginal_powers"],
        "joint_power_claim": "primary_joint_information_model_frozen",
        "joint_concordance_power_claim": power["joint_concordance_power_claim"],
        "technical_repeats_increase_independent_n": False,
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "artifact_sha256": artifact_digests,
    }
    return {
        FEASIBILITY_PATH: canonical_json_bytes(feasibility),
        SAMPLE_SIZE_PATH: canonical_json_bytes(sample_size),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    if args.check:
        mismatches = [
            path
            for path, payload in outputs.items()
            if not path.is_file() or path.read_bytes() != payload
        ]
        if mismatches:
            for path in mismatches:
                print(
                    f"feasibility-plan artifact drift: {path.relative_to(ROOT)}",
                    file=sys.stderr,
                )
            return 1
        print("biological Top-K feasibility artifacts reproduce byte-for-byte")
        return 0
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(outputs)} Phase 1 feasibility artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
