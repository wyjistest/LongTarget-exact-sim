#!/usr/bin/env python3
"""Build the Phase 1 workload-level joint information model and simulation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
CONTRACT_PATH = ROOT / "reproduce/biological_topk/contract.py"
MODEL_PATH = PAPER / "joint_information_model.json"
SIMULATION_PATH = PAPER / "joint_information_simulation.json"

N_PANEL = 178
N_BINARY_REQUIRED = 124
QUOTAS = {"short": 60, "medium": 59, "large": 59}
REFERENCE_NONEMPTY_REQUIRED = 60
REFERENCE_SITES_REQUIRED = 240
P_ELIGIBLE_CONSERVATIVE = 0.75
OUTER_SEED = 20260731
INNER_SEED = 20260801
RECHECK_SEED = 20260802
OUTER_REPLICATES = 2000
INNER_INITIAL = 10000
INNER_MAXIMUM = 100000
MC_HALFWIDTH_MAX = 0.005
WILSON_Z_95 = 1.959963984540054


def load_contract():
    spec = importlib.util.spec_from_file_location("biological_topk_information_contract", CONTRACT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CONTRACT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii")


def exact_candidate_count(contract: Any, path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        required = {"QueryStart", "QueryEnd", "Nt(bp)"}
        if not required <= set(fields):
            raise ValueError(f"candidate-count source lacks required fields: {path}")
        rows = list(reader)
    clustered = contract.cluster_legacy(
        [
            contract.LegacyRow(
                int(row["QueryStart"]),
                int(row["QueryEnd"]),
                int(row["Nt(bp)"]),
                index,
            )
            for index, row in enumerate(rows)
        ]
    )
    return min(5, len({row.motif for row in clustered if row.motif != 0}))


def single_output(directory: Path, pattern: str = "*TFOsorted") -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one output in {directory}, found {len(matches)}")
    return matches[0]


def planning_row(
    *,
    stratum: str,
    workload_id: str,
    development_unit_id: str,
    reference_count: int,
    source_path: Path,
    evidence_family: str,
) -> dict[str, Any]:
    nonempty = int(reference_count > 0)
    return {
        "target_scale_stratum": stratum,
        "workload_id": workload_id,
        "development_unit_id": development_unit_id,
        "denominator_eligible_indicator": 1,
        "reference_nonempty_indicator": nonempty,
        "reference_candidate_site_count": reference_count,
        "evidence_family": evidence_family,
        "source_path": source_path.relative_to(ROOT).as_posix(),
        "source_sha256": sha256_file(source_path),
        "technical_repeats_collapsed": True,
    }


def build_planning_rows(contract: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    short_root = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout"
    for directory in sorted(short_root.glob("v2hold_vh*__repeat00_a")):
        output = single_output(directory / "output")
        workload_id = directory.name.split("__", 1)[0].removeprefix("v2hold_")
        rows.append(
            planning_row(
                stratum="short",
                workload_id=workload_id,
                development_unit_id=workload_id,
                reference_count=exact_candidate_count(contract, output),
                source_path=output,
                evidence_family="canonical_hybrid_v2_fresh_holdout_development",
            )
        )

    medium_root = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization"
    for directory in sorted(medium_root.glob("g*__pair01__baseline__0")):
        output = single_output(directory / "output")
        workload_id = directory.name.split("__pair", 1)[0]
        rows.append(
            planning_row(
                stratum="medium",
                workload_id=workload_id,
                development_unit_id=workload_id,
                reference_count=exact_candidate_count(contract, output),
                source_path=output,
                evidence_family="paper_generalization_2mb_development",
            )
        )

    phase2 = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core"
    c1_topk = phase2 / "c1_h19_chr21_chr22_fast_topk__pair01__baseline__0/output/topk_rows.tsv"
    with c1_topk.open(newline="", encoding="utf-8") as handle:
        c1_rows = [row for row in csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t")]
    c1_count = len([row for row in c1_rows if row["mode"] == "score"])
    rows.append(
        planning_row(
            stratum="large",
            workload_id="c1_h19_chr21_chr22_full",
            development_unit_id="H19_chr21_chr22_full",
            reference_count=min(5, c1_count),
            source_path=c1_topk,
            evidence_family="paper_chromosome_scale_fast_topk",
        )
    )

    c6_details = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase4-ablation-resource/pairs-v1/c6_exact_kcnq_segment_chr22__pair01__0/top5-details.tsv"
    with c6_details.open(newline="", encoding="utf-8") as handle:
        detail_rows = list(csv.DictReader(handle, delimiter="\t"))
    c6_count = sum(
        row["side"] == "baseline" and row["kind"] == "clustered" and row["mode"] == "score"
        for row in detail_rows
    )
    rows.append(
        planning_row(
            stratum="large",
            workload_id="c6_kcnq1ot1_chr22_full",
            development_unit_id="KCNQ1OT1_chr22_full",
            reference_count=min(5, c6_count),
            source_path=c6_details,
            evidence_family="paper_chromosome_scale_exact_column",
        )
    )
    if Counter(row["target_scale_stratum"] for row in rows) != Counter(
        {"short": 48, "medium": 13, "large": 2}
    ):
        raise ValueError("planning evidence row counts drifted")
    return rows


def tuple_distribution(rows: Iterable[dict[str, Any]]) -> list[tuple[tuple[int, int, int], float]]:
    values = [
        (
            int(row["denominator_eligible_indicator"]),
            int(row["reference_nonempty_indicator"]),
            int(row["reference_candidate_site_count"]),
        )
        for row in rows
    ]
    counts = Counter(values)
    total = len(values)
    return sorted((key, count / total) for key, count in counts.items())


def simulate_panels(
    rng: np.random.Generator,
    distributions: dict[str, list[tuple[tuple[int, int, int], float]]],
    simulations: int,
) -> dict[str, np.ndarray]:
    eligible_observed = np.zeros(simulations, dtype=np.int16)
    nonempty = np.zeros(simulations, dtype=np.int16)
    sites = np.zeros(simulations, dtype=np.int16)
    for stratum in ("short", "medium", "large"):
        distribution = distributions[stratum]
        tuples = [entry[0] for entry in distribution]
        probabilities = np.asarray([entry[1] for entry in distribution], dtype=np.float64)
        probabilities /= probabilities.sum()
        category_counts = rng.multinomial(QUOTAS[stratum], probabilities, size=simulations)
        eligible_observed += category_counts @ np.asarray([item[0] for item in tuples], dtype=np.int16)
        nonempty += category_counts @ np.asarray([item[1] for item in tuples], dtype=np.int16)
        sites += category_counts @ np.asarray([item[2] for item in tuples], dtype=np.int16)
    eligible = rng.binomial(eligible_observed, P_ELIGIBLE_CONSERVATIVE)
    outcomes = {
        "eligible_count": eligible >= N_BINARY_REQUIRED,
        "reference_nonempty_count": nonempty >= REFERENCE_NONEMPTY_REQUIRED,
        "total_reference_candidate_sites": sites >= REFERENCE_SITES_REQUIRED,
    }
    outcomes["joint"] = (
        outcomes["eligible_count"]
        & outcomes["reference_nonempty_count"]
        & outcomes["total_reference_candidate_sites"]
    )
    return outcomes


def wilson_halfwidth(successes: int, trials: int) -> float:
    proportion = successes / trials
    denominator = 1 + WILSON_Z_95**2 / trials
    return (
        WILSON_Z_95
        * math.sqrt(
            proportion * (1 - proportion) / trials
            + WILSON_Z_95**2 / (4 * trials**2)
        )
        / denominator
    )


def adaptive_probability(
    rng: np.random.Generator,
    distributions: dict[str, list[tuple[tuple[int, int, int], float]]],
) -> dict[str, Any]:
    trials = 0
    successes = {
        "eligible_count": 0,
        "reference_nonempty_count": 0,
        "total_reference_candidate_sites": 0,
        "joint": 0,
    }
    next_total = INNER_INITIAL
    while True:
        additional = next_total - trials
        outcomes = simulate_panels(rng, distributions, additional)
        for name, values in outcomes.items():
            successes[name] += int(values.sum())
        trials = next_total
        halfwidth = wilson_halfwidth(successes["joint"], trials)
        if halfwidth <= MC_HALFWIDTH_MAX or trials >= INNER_MAXIMUM:
            return {
                "successes": successes["joint"],
                "simulations": trials,
                "probability": successes["joint"] / trials,
                "wilson_95_halfwidth": halfwidth,
                "precision_pass": halfwidth <= MC_HALFWIDTH_MAX,
                "marginal_successes": {
                    name: value for name, value in successes.items() if name != "joint"
                },
                "marginal_probabilities": {
                    name: value / trials for name, value in successes.items() if name != "joint"
                },
            }
        next_total = min(INNER_MAXIMUM, trials * 2)


def empirical_distributions(rows: list[dict[str, Any]]) -> dict[str, list[tuple[tuple[int, int, int], float]]]:
    return {
        stratum: tuple_distribution(row for row in rows if row["target_scale_stratum"] == stratum)
        for stratum in ("short", "medium", "large")
    }


def bootstrap_distributions(
    rows: list[dict[str, Any]], rng: np.random.Generator
) -> dict[str, list[tuple[tuple[int, int, int], float]]]:
    result: dict[str, list[tuple[tuple[int, int, int], float]]] = {}
    for stratum in ("short", "medium", "large"):
        stratum_rows = [row for row in rows if row["target_scale_stratum"] == stratum]
        indexes = rng.integers(0, len(stratum_rows), size=len(stratum_rows))
        result[stratum] = tuple_distribution(stratum_rows[int(index)] for index in indexes)
    return result


def serialize_distribution(
    distribution: list[tuple[tuple[int, int, int], float]]
) -> list[dict[str, Any]]:
    return [
        {
            "denominator_eligible_indicator": values[0],
            "reference_nonempty_indicator": values[1],
            "reference_candidate_site_count": values[2],
            "probability": format(probability, ".17g"),
        }
        for values, probability in distribution
    ]


def build() -> dict[Path, bytes]:
    contract = load_contract()
    rows = build_planning_rows(contract)
    empirical = empirical_distributions(rows)
    model = {
        "schema_version": 1,
        "reference_candidate_count_definition": (
            "deduplicated canonical candidate-site count in CPU A score ranking, capped at K=5; "
            "score/stability/Nt lists are not added"
        ),
        "planning_unit": "workload_after_collapsing_technical_repeats",
        "planning_rows": rows,
        "row_count_by_stratum": dict(sorted(Counter(row["target_scale_stratum"] for row in rows).items())),
        "empirical_tuple_distributions": {
            stratum: serialize_distribution(empirical[stratum])
            for stratum in ("short", "medium", "large")
        },
        "p_reference_nonempty_planning": "1",
        "candidate_count_distributions": {
            stratum: {
                str(count): sum(
                    probability
                    for values, probability in empirical[stratum]
                    if values[2] == count
                )
                for count in range(6)
            }
            for stratum in ("short", "medium", "large")
        },
        "eligibility_conservatism": {
            "observed_development_indicator_rate": "1",
            "planning_probability": "0.75",
            "reason": "protocol default retained because historical all-eligible rows do not identify fresh technical failure or clean-double-empty risk",
            "simulation_rule": "sample joint tuple, then Bernoulli-thin each observed-eligible workload at p=0.75; observed-ineligible remains ineligible",
        },
        "joint_correlation_report": {
            "eligible_nonempty": "undefined_zero_variance_in_observed_rows",
            "eligible_candidate_count": "undefined_zero_variance_in_observed_eligibility",
            "nonempty_candidate_count": "undefined_zero_variance_in_observed_nonempty",
        },
        "limitations": [
            "large-stratum development evidence has only two distinct collapsed workloads",
            "technical repeats do not increase development row count",
            "outer bootstrap quantifies empirical-distribution uncertainty but cannot create unobserved tuple categories",
        ],
    }

    outer_rng = np.random.default_rng(OUTER_SEED)
    child_sequences = np.random.SeedSequence(INNER_SEED).spawn(OUTER_REPLICATES + 1)
    point = adaptive_probability(np.random.default_rng(child_sequences[0]), empirical)
    outer_results: list[dict[str, Any]] = []
    outer_distributions: list[dict[str, list[tuple[tuple[int, int, int], float]]]] = []
    for replicate in range(OUTER_REPLICATES):
        distribution = bootstrap_distributions(rows, outer_rng)
        outer_distributions.append(distribution)
        result = adaptive_probability(
            np.random.default_rng(child_sequences[replicate + 1]),
            distribution,
        )
        outer_results.append({"outer_replicate": replicate + 1, **result})
    if not all(result["precision_pass"] for result in outer_results) or not point["precision_pass"]:
        raise ValueError("joint information inner Monte Carlo precision was not met")
    ordered = sorted(outer_results, key=lambda row: (row["probability"], row["outer_replicate"]))
    quantile_rank = math.ceil(0.05 * OUTER_REPLICATES)
    boundary = ordered[quantile_rank - 1]
    lcb = float(boundary["probability"])
    marginal_names = (
        "eligible_count",
        "reference_nonempty_count",
        "total_reference_candidate_sites",
    )
    marginal_lcbs = {
        name: sorted(float(result["marginal_probabilities"][name]) for result in outer_results)[
            quantile_rank - 1
        ]
        for name in marginal_names
    }

    recheck_indexes = sorted(
        {
            ordered[index]["outer_replicate"] - 1
            for index in range(max(0, quantile_rank - 3), min(OUTER_REPLICATES, quantile_rank + 2))
        }
    )
    recheck_sequences = np.random.SeedSequence(RECHECK_SEED).spawn(len(recheck_indexes) + 1)
    empirical_recheck = adaptive_probability(np.random.default_rng(recheck_sequences[0]), empirical)
    boundary_rechecks = []
    for sequence, outer_index in zip(recheck_sequences[1:], recheck_indexes):
        original = outer_results[outer_index]
        recheck = adaptive_probability(
            np.random.default_rng(sequence),
            outer_distributions[outer_index],
        )
        boundary_rechecks.append(
            {
                "outer_replicate": outer_index + 1,
                "original_probability": format(float(original["probability"]), ".17g"),
                "recheck_probability": format(float(recheck["probability"]), ".17g"),
                "absolute_difference": format(
                    abs(float(original["probability"]) - float(recheck["probability"])),
                    ".17g",
                ),
                "recheck_simulations": recheck["simulations"],
                "recheck_halfwidth": format(float(recheck["wilson_95_halfwidth"]), ".17g"),
            }
        )

    count_distribution = Counter(int(result["simulations"]) for result in outer_results)
    halfwidths = [float(result["wilson_95_halfwidth"]) for result in outer_results]
    simulation = {
        "schema_version": 1,
        "model_sha256": hashlib.sha256(canonical_json_bytes(model)).hexdigest(),
        "N_panel": N_PANEL,
        "stratum_quotas": QUOTAS,
        "joint_success_thresholds": {
            "eligible_count": N_BINARY_REQUIRED,
            "reference_nonempty_count": REFERENCE_NONEMPTY_REQUIRED,
            "total_reference_candidate_sites": REFERENCE_SITES_REQUIRED,
        },
        "joint_outer_bootstrap_seed": OUTER_SEED,
        "joint_inner_simulation_seed": INNER_SEED,
        "independent_recheck_seed": RECHECK_SEED,
        "joint_outer_bootstrap_replicates": OUTER_REPLICATES,
        "joint_inner_panel_simulations_initial": INNER_INITIAL,
        "joint_inner_panel_simulations_max": INNER_MAXIMUM,
        "joint_inner_mc_halfwidth_max": format(MC_HALFWIDTH_MAX, ".17g"),
        "inner_mc_interval": "two-sided_95_percent_Wilson",
        "joint_outer_lcb_quantile": "0.05",
        "outer_quantile_definition": "q_(ceil(0.05*B))_without_interpolation",
        "outer_quantile_order_rank": quantile_rank,
        "joint_information_probability_point": format(float(point["probability"]), ".17g"),
        "point_inner_successes": point["successes"],
        "point_inner_simulations": point["simulations"],
        "point_inner_mc_halfwidth": format(float(point["wilson_95_halfwidth"]), ".17g"),
        "marginal_probability_point": {
            name: format(float(point["marginal_probabilities"][name]), ".17g")
            for name in marginal_names
        },
        "marginal_probability_outer_lcb": {
            name: format(marginal_lcbs[name], ".17g") for name in marginal_names
        },
        "point_marginal_successes": {
            name: int(point["marginal_successes"][name]) for name in marginal_names
        },
        "joint_information_probability_lcb": format(lcb, ".17g"),
        "joint_information_gate_threshold": "0.95",
        "joint_information_gate_pass": lcb >= 0.95,
        "inner_simulation_count_distribution": {
            str(key): value for key, value in sorted(count_distribution.items())
        },
        "inner_mc_halfwidth_min": format(min(halfwidths), ".17g"),
        "inner_mc_halfwidth_max_observed": format(max(halfwidths), ".17g"),
        "joint_inner_mc_precision_pass": True,
        "outer_q_distribution": [
            {
                "outer_replicate": int(result["outer_replicate"]),
                "successes": int(result["successes"]),
                "simulations": int(result["simulations"]),
                "q": format(float(result["probability"]), ".17g"),
                "mc_halfwidth": format(float(result["wilson_95_halfwidth"]), ".17g"),
            }
            for result in outer_results
        ],
        "independent_seed_recheck": {
            "empirical_original": format(float(point["probability"]), ".17g"),
            "empirical_recheck": format(float(empirical_recheck["probability"]), ".17g"),
            "empirical_absolute_difference": format(
                abs(float(point["probability"]) - float(empirical_recheck["probability"])),
                ".17g",
            ),
            "boundary_outer_replicates": boundary_rechecks,
        },
        "inner_simulations_are_independent_scientific_evidence": False,
    }
    if not simulation["joint_information_gate_pass"]:
        raise ValueError("joint information probability LCB is below 0.95")
    return {
        MODEL_PATH: canonical_json_bytes(model),
        SIMULATION_PATH: canonical_json_bytes(simulation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    if args.check:
        mismatches = [path for path, payload in outputs.items() if not path.is_file() or path.read_bytes() != payload]
        if mismatches:
            for path in mismatches:
                print(f"joint information artifact drift: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("biological Top-K joint information artifacts reproduce byte-for-byte")
        return 0
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(outputs)} Phase 1 joint-information artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
