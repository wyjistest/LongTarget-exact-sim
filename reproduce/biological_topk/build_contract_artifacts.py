#!/usr/bin/env python3
"""Build deterministic Phase 1 contract, fixture, and power artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
CONTRACT_PATH = ROOT / "reproduce/biological_topk/contract.py"
CLUSTER_FIXTURES = PAPER / "legacy_clustering_fixtures.tsv"
COORDINATE_FIXTURES = PAPER / "coordinate_golden_fixtures.tsv"
COORDINATE_MAPPING_TABLE = ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"
SCORE_AUDIT = PAPER / "score_integrality_audit.tsv"
SCORE_DECISION = PAPER / "score_integrality_decision.json"
POWER_PLAN = PAPER / "concordance_power_plan.json"
EXPERIMENTAL_PLAN = PAPER / "experimental_power_simulation_plan.json"
ENVELOPE_PATH = PAPER / "operating_envelope.json"
CONTRACT_SPEC = PAPER / "contract_spec.json"

CLUSTER_FIELDS = (
    "fixture_id",
    "row_order",
    "raw_QueryStart",
    "raw_QueryEnd",
    "raw_Nt_bp",
    "expected_eligible",
    "expected_legacy_midpoint",
    "expected_motif",
    "expected_center",
    "expected_neartriplex",
    "source_semantics",
)
COORDINATE_FIELDS = (
    "fixture_id",
    "evidence_kind",
    "status",
    "raw_QueryStart",
    "raw_QueryEnd",
    "raw_StartInSeq",
    "raw_EndInSeq",
    "raw_StartInGenome",
    "raw_EndInGenome",
    "raw_Strand",
    "raw_Direction",
    "raw_Chr",
    "target_length",
    "target_region_start0",
    "target_source_path",
    "target_sequence_inline",
    "expected_query_start0",
    "expected_query_end0",
    "expected_target_start0",
    "expected_target_end0",
    "expected_genome_start0",
    "expected_genome_end0",
    "expected_ungapped_tts",
    "source_code_path",
)
COORDINATE_MAPPING_FIELDS = (
    "strand_label",
    "direction_label",
    "internal_strand_code",
    "raw_StartInSeq_basis",
    "raw_EndInSeq_basis",
    "interval_closure",
    "orientation_relative_to_target_fasta",
    "forward_target_interval_formula",
    "genome_interval_formula",
    "tts_sequence_orientation_rule",
    "query_coordinate_formula",
    "source_code_path_and_line_range",
    "status",
)
SCORE_FIELDS = (
    "source_path_class",
    "source_code_path",
    "file_count",
    "row_count",
    "minimum_score_decimal",
    "maximum_score_decimal",
    "nonintegral_count",
    "all_integral",
    "raw_score_stream_sha256",
)


def load_contract():
    spec = importlib.util.spec_from_file_location("biological_topk_phase1_contract", CONTRACT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CONTRACT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii")


def render_tsv(fields: tuple[str, ...], rows: Iterable[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def fasta_sequence(path: Path) -> str:
    sequence = "".join(
        line.strip() for line in path.read_text(encoding="ascii").splitlines()
        if line and not line.startswith(">")
    ).upper()
    if not sequence:
        raise ValueError(f"empty FASTA: {path}")
    return sequence


def cluster_fixture_rows(contract: Any) -> list[dict[str, Any]]:
    cases = {
        "nt_boundary": ((101, 149, 49), (101, 150, 50), (101, 151, 51)),
        "midpoint_parity": ((100, 151, 51), (101, 151, 51), (131, 181, 51)),
        "dynamic_map_strict_ties": (
            (101, 151, 51),
            (131, 181, 51),
            (161, 211, 51),
            (101, 151, 52),
        ),
        "motif_assignment_order": (
            (200, 260, 61),
            (190, 250, 61),
            (220, 280, 61),
            (500, 560, 61),
        ),
    }
    expected = {
        "nt_boundary": ((0, 0, 0, 0), (0, 0, 0, 0), (126, 1, 125, 0)),
        "midpoint_parity": ((125, 1, 124, 0), (126, 1, 124, 14), (156, 2, 155, 0)),
        "dynamic_map_strict_ties": (
            (126, 1, 125, 0),
            (156, 2, 155, 0),
            (186, 3, 185, 0),
            (126, 1, 125, 0),
        ),
        "motif_assignment_order": (
            (230, 1, 221, 0),
            (220, 1, 221, 5),
            (250, 2, 249, 0),
            (530, 3, 529, 0),
        ),
    }
    rows: list[dict[str, Any]] = []
    for fixture_id, values in cases.items():
        actual = contract.cluster_legacy(
            [contract.LegacyRow(start, end, nt, index) for index, (start, end, nt) in enumerate(values)]
        )
        actual_values = tuple((row.middle, row.motif, row.center, row.neartriplex) for row in actual)
        if actual_values != expected[fixture_id]:
            raise ValueError(f"legacy clustering fixture drift: {fixture_id}")
        for row_order, ((start, end, nt), result) in enumerate(zip(values, expected[fixture_id]), 1):
            middle, motif, center, near = result
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "row_order": row_order,
                    "raw_QueryStart": start,
                    "raw_QueryEnd": end,
                    "raw_Nt_bp": nt,
                    "expected_eligible": int(nt > 50),
                    "expected_legacy_midpoint": middle,
                    "expected_motif": motif,
                    "expected_center": center,
                    "expected_neartriplex": near,
                    "source_semantics": "fasim/Fasim-LongTarget.cpp:29089-29179",
                }
            )
    return rows


def coordinate_row(
    contract: Any,
    *,
    fixture_id: str,
    evidence_kind: str,
    raw: dict[str, str | int],
    target_sequence: str,
    target_region_start0: int,
    target_source_path: str,
    target_sequence_inline: str = "NA",
) -> dict[str, Any]:
    coordinates = contract.canonicalize_coordinates(
        raw_query_start=int(raw["QueryStart"]),
        raw_query_end=int(raw["QueryEnd"]),
        raw_target_start=int(raw["StartInSeq"]),
        raw_target_end=int(raw["EndInSeq"]),
        strand=str(raw["Strand"]),
        direction=str(raw["Direction"]),
        target_length=len(target_sequence),
        target_region_start0=target_region_start0,
    )
    expected_tts = contract.reconstruct_tts(target_sequence, coordinates, str(raw["Strand"]))
    if "TTS sequence" in raw and contract.normalize_ungapped(str(raw["TTS sequence"])) != expected_tts:
        raise ValueError(f"historical TTS reconstruction mismatch: {fixture_id}")
    return {
        "fixture_id": fixture_id,
        "evidence_kind": evidence_kind,
        "status": "reachable_current_fast_path",
        "raw_QueryStart": raw["QueryStart"],
        "raw_QueryEnd": raw["QueryEnd"],
        "raw_StartInSeq": raw["StartInSeq"],
        "raw_EndInSeq": raw["EndInSeq"],
        "raw_StartInGenome": raw.get("StartInGenome", "NA"),
        "raw_EndInGenome": raw.get("EndInGenome", "NA"),
        "raw_Strand": raw["Strand"],
        "raw_Direction": raw["Direction"],
        "raw_Chr": raw.get("Chr", "synthetic"),
        "target_length": len(target_sequence),
        "target_region_start0": target_region_start0,
        "target_source_path": target_source_path,
        "target_sequence_inline": target_sequence_inline,
        "expected_query_start0": coordinates.query_start0,
        "expected_query_end0": coordinates.query_end0,
        "expected_target_start0": coordinates.target_start0,
        "expected_target_end0": coordinates.target_end0,
        "expected_genome_start0": coordinates.genome_start0,
        "expected_genome_end0": coordinates.genome_end0,
        "expected_ungapped_tts": expected_tts,
        "source_code_path": "fasim/fastsim.h:3701-3712;fasim/Fasim-LongTarget.cpp:27763-27850",
    }


def coordinate_fixture_rows(contract: Any) -> list[dict[str, Any]]:
    target = "ACGTTGCA"
    synthetic = (
        ("paraplus_first_base", "ParaPlus", 1, 1),
        ("antiminus_last_base", "AntiMinus", 8, 8),
        ("paraminus_first_base", "ParaMinus", 0, 0),
        ("antiplus_last_base", "AntiPlus", 7, 7),
        ("paraminus_multibase", "ParaMinus", 2, 5),
    )
    rows = [
        coordinate_row(
            contract,
            fixture_id=fixture_id,
            evidence_kind="synthetic_boundary",
            raw={
                "QueryStart": 1 if "first" in fixture_id else 2,
                "QueryEnd": 1 if "first" in fixture_id else 5,
                "StartInSeq": start,
                "EndInSeq": end,
                "StartInGenome": "NA",
                "EndInGenome": "NA",
                "Strand": strand,
                "Direction": "R",
                "Chr": "synthetic_target",
            },
            target_sequence=target,
            target_region_start0=100,
            target_source_path="inline",
            target_sequence_inline=target,
        )
        for fixture_id, strand, start, end in synthetic
    ]

    target_path = ROOT / "reproduce/bioinformatics/holdout_inputs/targets/ht02_ENSG00000198722_chr9_35159829_35162329.fa"
    historical_target = fasta_sequence(target_path)
    historical_specs = (
        (
            "hq10_ht02_paraminus_last_interval",
            ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1/formal/hq10_ht02__repeat00/authority/output",
            6,
        ),
        (
            "hq11_ht02_antiplus",
            ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1/formal/hq11_ht02__repeat00/authority/output",
            6,
        ),
        (
            "hq11_ht02_antiminus",
            ROOT / ".paper-artifacts/bioinformatics-phase2-holdout-v1/formal/hq11_ht02__repeat00/authority/output",
            7,
        ),
    )
    for fixture_id, output_dir, zero_based_row in historical_specs:
        output_path = next(output_dir.glob("*TFOsorted"))
        with output_path.open(newline="", encoding="utf-8") as handle:
            output_rows = list(csv.DictReader(handle, delimiter="\t"))
        raw = output_rows[zero_based_row]
        rows.append(
            coordinate_row(
                contract,
                fixture_id=fixture_id,
                evidence_kind="frozen_hq10_hq11",
                raw=raw,
                target_sequence=historical_target,
                target_region_start0=35_159_828,
                target_source_path=target_path.relative_to(ROOT).as_posix(),
            )
        )

    for strand in sorted(contract.SUPPORTED_STRANDS):
        rows.append(
            {
                "fixture_id": f"{strand.lower()}_direction_l_unreachable",
                "evidence_kind": "source_reachability",
                "status": "unreachable_by_current_runtime",
                "raw_QueryStart": "NA",
                "raw_QueryEnd": "NA",
                "raw_StartInSeq": "NA",
                "raw_EndInSeq": "NA",
                "raw_StartInGenome": "NA",
                "raw_EndInGenome": "NA",
                "raw_Strand": strand,
                "raw_Direction": "L",
                "raw_Chr": "NA",
                "target_length": "NA",
                "target_region_start0": "NA",
                "target_source_path": "NA",
                "target_sequence_inline": "NA",
                "expected_query_start0": "NA",
                "expected_query_end0": "NA",
                "expected_target_start0": "NA",
                "expected_target_end0": "NA",
                "expected_genome_start0": "NA",
                "expected_genome_end0": "NA",
                "expected_ungapped_tts": "NA",
                "source_code_path": "fasim/fastsim.h:3703-3712;fasim/Fasim-LongTarget.cpp:29323-29326",
            }
        )
    return rows


def coordinate_mapping_rows() -> list[dict[str, str]]:
    strand_rules = {
        "ParaPlus": {
            "internal_strand_code": "reverse=1;strand=0",
            "basis": "1_based",
            "orientation": "forward",
            "interval": "[raw_StartInSeq-1,raw_EndInSeq)",
            "tts": "forward_target_subsequence",
        },
        "ParaMinus": {
            "internal_strand_code": "reverse=1;strand=1",
            "basis": "0_based",
            "orientation": "reverse_complement",
            "interval": "[raw_StartInSeq,raw_EndInSeq+1)",
            "tts": "reverse_complement_forward_target_subsequence",
        },
        "AntiPlus": {
            "internal_strand_code": "reverse=-1;strand=0",
            "basis": "0_based",
            "orientation": "reverse",
            "interval": "[raw_StartInSeq,raw_EndInSeq+1)",
            "tts": "reverse_forward_target_subsequence",
        },
        "AntiMinus": {
            "internal_strand_code": "reverse=-1;strand=1",
            "basis": "1_based",
            "orientation": "complement",
            "interval": "[raw_StartInSeq-1,raw_EndInSeq)",
            "tts": "complement_forward_target_subsequence",
        },
    }
    rows: list[dict[str, str]] = []
    for strand in ("ParaPlus", "ParaMinus", "AntiPlus", "AntiMinus"):
        rule = strand_rules[strand]
        for direction in ("R", "L"):
            reachable = direction == "R"
            rows.append(
                {
                    "strand_label": strand,
                    "direction_label": direction,
                    "internal_strand_code": rule["internal_strand_code"],
                    "raw_StartInSeq_basis": rule["basis"] if reachable else "NA_unreachable",
                    "raw_EndInSeq_basis": rule["basis"] if reachable else "NA_unreachable",
                    "interval_closure": "inclusive_raw" if reachable else "NA_unreachable",
                    "orientation_relative_to_target_fasta": rule["orientation"] if reachable else "NA_unreachable",
                    "forward_target_interval_formula": rule["interval"] if reachable else "NA_unreachable",
                    "genome_interval_formula": (
                        "[target_region_start0+target_start0,target_region_start0+target_end0)"
                        if reachable
                        else "NA_unreachable"
                    ),
                    "tts_sequence_orientation_rule": rule["tts"] if reachable else "NA_unreachable",
                    "query_coordinate_formula": (
                        "[raw_QueryStart-1,raw_QueryEnd) from 1_based_inclusive raw fields"
                        if reachable
                        else "NA_unreachable"
                    ),
                    "source_code_path_and_line_range": (
                        "fasim/fastsim.h:3701-3722;fasim/Fasim-LongTarget.cpp:27757-27851,29323-29373"
                    ),
                    "status": "reachable_current_fast_path" if reachable else "unreachable_by_current_runtime",
                }
            )
    return rows


def score_groups() -> dict[str, list[Path]]:
    short_root = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout"
    medium_root = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization"
    large_root = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core"
    return {
        "current_cpu_authority_short": sorted(short_root.glob("v2hold_vh*__repeat00_a/output/*TFOsorted")),
        "current_hybrid_candidate_short": sorted(short_root.glob("v2hold_vh*__repeat00_h/output/*TFOsorted")),
        "historical_fast_topk_medium": sorted(medium_root.glob("g*__pair01__baseline__0/output/*TFOsorted")),
        "historical_fast_topk_large": [
            large_root / "c1_h19_chr21_chr22_fast_topk__pair01__baseline__0/output/topk-TFOsorted.lite",
            large_root / "c4_h19_chr21_two_slot__pair01__baseline__0/output/chr21-H19_0_2812-chr21-TFOsorted.lite",
            large_root / "c4_h19_chr22_two_slot__pair01__baseline__0/output/chr22-H19_0_2812-chr22-TFOsorted.lite",
        ],
    }


def score_audit_rows(contract: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group, paths in score_groups().items():
        if not paths or any(not path.is_file() for path in paths):
            raise ValueError(f"missing score audit evidence for {group}")
        digest = hashlib.sha256()
        minimum: Decimal | None = None
        maximum: Decimal | None = None
        row_count = 0
        nonintegral = 0
        for path in paths:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if "Score" not in (reader.fieldnames or ()):
                    raise ValueError(f"Score column missing from {path}")
                for record in reader:
                    raw = record["Score"]
                    value = contract.parse_decimal(raw)
                    digest.update(raw.encode("ascii") + b"\n")
                    row_count += 1
                    minimum = value if minimum is None else min(minimum, value)
                    maximum = value if maximum is None else max(maximum, value)
                    nonintegral += int(value != value.to_integral_value())
        rows.append(
            {
                "source_path_class": group,
                "source_code_path": "fasim/fastsim.h:3714-3724",
                "file_count": len(paths),
                "row_count": row_count,
                "minimum_score_decimal": contract.canonical_decimal(minimum or Decimal(0)),
                "maximum_score_decimal": contract.canonical_decimal(maximum or Decimal(0)),
                "nonintegral_count": nonintegral,
                "all_integral": int(nonintegral == 0),
                "raw_score_stream_sha256": digest.hexdigest(),
            }
        )
    return rows


def build_power_plan(contract: Any) -> dict[str, Any]:
    fixture_ns = (60, 89, 100, 123, 124, 150)
    fixtures = []
    for n in fixture_ns:
        minimum, power = contract.exact_gate_power(n)
        fixtures.append(
            {
                "n": n,
                "k_min": minimum,
                "allowed_failures": n - int(minimum),
                "power_at_p_alt": contract.canonical_decimal(power),
            }
        )
    required_n, required_k, achieved_power = contract.required_binary_n()
    panel_n, eligibility_probability = contract.required_panel_n(required_n)
    return {
        "schema_version": 1,
        "method": "exact enumeration with one-sided Clopper-Pearson lower bound",
        "alpha": "0.05",
        "required_one_sided_lcb": "0.95",
        "p_alt": "0.99",
        "minimum_primary_gate_power": "0.80",
        "minimum_denominator_floor": 60,
        "n_binary_required": required_n,
        "k_min": required_k,
        "allowed_failures": required_n - required_k,
        "achieved_power": contract.canonical_decimal(achieved_power),
        "p_binary_denominator_eligible_planning": "0.75",
        "eligibility_probability_target": "0.95",
        "default_panel_n_fixture": panel_n,
        "default_panel_eligibility_probability": contract.canonical_decimal(eligibility_probability),
        "clopper_pearson_fixtures": {
            "60_of_60": contract.canonical_decimal(contract.clopper_pearson_lower(60, 60)),
            "59_of_60": contract.canonical_decimal(contract.clopper_pearson_lower(59, 60)),
        },
        "power_fixtures": fixtures,
        "secondary_marginal_powers": {
            endpoint: contract.canonical_decimal(achieved_power)
            for endpoint in (
                "stability_complete_set",
                "nt_complete_set",
                "score_top1",
                "stability_top1",
                "nt_top1",
            )
        },
        "joint_concordance_power_claim": "not_made",
        "fixed_sequence": [
            "score_complete_set",
            "stability_complete_set",
            "nt_complete_set",
            "score_top1",
            "stability_top1",
            "nt_top1",
        ],
    }


def operating_envelope(contract: Any) -> dict[str, Any]:
    parameters = {
        "runtime_mode": "normal_triplex_fast_topk",
        "rule": 0,
        "strand_request": 0,
        "cut_length": 5000,
        "overlap_length": 100,
        "nt_min_runtime": 20,
        "nt_max_runtime": 100000,
        "score_min": "0",
        "minimum_identity_percent": "60",
        "minimum_stability": "1",
        "penalty_t": -1000,
        "penalty_c": 0,
        "cluster_distance": 15,
        "minimum_nt_rule": "strict_greater_than",
        "minimum_nt_bp": 50,
        "k": 5,
    }
    parameter_digest = contract.canonical_json_sha256(parameters)
    return {
        "schema_version": 1,
        "contract_name": "biological_topk_candidate_site_v1",
        "runtime_mode": "normal_triplex_fast_topk",
        "supported_runtime_modes": ["cpu_fast_topk_authority", "canonical_hybrid_v2_candidate"],
        "query_length_min": 500,
        "query_length_max": 2812,
        "query_input_alphabet": "ACGT",
        "target_input_alphabet": "ACGTN",
        "normalized_output_alphabet": "ACGTN",
        "target_scale_recipes": [
            {"stratum": "short", "recipe_id": "grch38_tss_centered_4097_v1", "length_bp": 4097},
            {"stratum": "medium", "recipe_id": "grch38_tss_centered_2000001_v1", "length_bp": 2000001},
            {"stratum": "large", "recipe_id": "grch38_tss_centered_10000001_v1", "length_bp": 10000001},
        ],
        "parameters": parameters,
        "parameter_bundle_sha256": parameter_digest,
        "hardware": {
            "gpu_model": "NVIDIA GeForce RTX 4090",
            "gpu_count": 2,
            "gpu_memory_mib_each": 24564,
            "compute_capability": "8.9",
            "driver_version": "555.42.06",
            "cuda_version": "12.5",
            "workers_per_gpu": 1,
            "logical_worker_count": 2,
        },
        "batching_policy": {
            "FASIM_ALIGN_GASAL2_BATCH": "20000",
            "FASIM_ALIGN_GASAL2_STREAMS": "3",
            "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "256",
        },
        "memory_guard": "fixed RTX4090 24564 MiB inventory; OOM is a technical failure",
        "oom_behavior": "technical_failure_binary_zero_no_retry",
        "unexpected_fallback_behavior": "technical_failure_binary_zero",
        "unsupported_input_behavior": "fail_closed_before_matching",
        "hardware_generality_claim": "single_gpu_generation_RTX4090_only",
        "source_code_defaults": "fasim/Fasim-LongTarget.cpp:28436-28470",
    }


def experimental_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "preregistered_before_dataset_inventory_and_predictions",
        "outer_independent_unit": "distinct_lncRNA",
        "minimum_distinct_lncRNAs": 5,
        "assay_coverage_rule": "at_least_two_if_two_or_more_input_eligible_types_exist",
        "plausible_prevalence_range": ["0.01", "0.10"],
        "regions_per_dataset_grid": [1000, 5000, 10000],
        "within_dataset_block_size_grid": [25, 50, 100],
        "within_dataset_correlation_grid": ["0.05", "0.10", "0.20"],
        "within_lncRNA_cross_assay_correlation_grid": ["0.25", "0.50", "0.75"],
        "expected_aucpr_range": ["0.05", "0.40"],
        "nested_dataset_counts_per_lncRNA": [1, 2, 3],
        "simulation_seed": 20260815,
        "simulation_replicates": 10000,
        "hierarchical_bootstrap": {
            "outer": "distinct_lncRNA",
            "nested_level_1": "dataset_or_assay_within_lncRNA",
            "nested_level_2": "chromosome_or_frozen_genomic_block",
            "pairing": "A_and_G_remain_paired_at_every_level",
            "replicates": 10000,
            "seed": 20260816,
            "interval": "one_sided_percentile_95",
            "shared_resample_index_for_all_endpoints": True,
        },
        "co_primary_endpoints": {
            "E1": {"estimand": "macro_lncRNA_GPU_minus_CPU_AUCPR", "lcb_threshold": "-0.02"},
            "E2": {"estimand": "macro_lncRNA_GPU_minus_CPU_recall_at_Pd", "lcb_threshold": "-0.05"},
            "E3": {"estimand": "macro_lncRNA_GPU_AUCPR_minus_prevalence", "lcb_threshold_strict": "0"},
            "E4": {"estimand": "macro_lncRNA_log_GPU_top_P_fold_enrichment", "lcb_threshold_strict": "0"},
        },
        "intersection_union_gate": "E1_AND_E2_AND_E3_AND_E4",
        "one_sided_alpha_each": "0.05",
        "zero_precision_rule": "automatic_E4_and_global_failure_no_pseudocount",
        "same_lncRNA_multiple_assays_increase_outer_n": False,
        "blocked_rule": "fewer_than_5_distinct_lncRNAs_or_nonidentifiable_one_sided_CI",
    }


def contract_spec(
    contract: Any,
    *,
    cluster_sha: str,
    coordinate_sha: str,
    coordinate_mapping_sha: str,
    envelope: dict[str, Any],
    power: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "contract_name": "biological_topk_candidate_site_v1",
        "scientific_object": "clustered_TFO_query_target_candidate_site",
        "claim_scope": "set_preservation_with_top1_retention",
        "rank_order_claim": "diagnostic_only",
        "ranking_mode_values": ["score", "stability", "nt"],
        "score_representation": "integral_exact",
        "k": 5,
        "row_eligibility": {"nt_operator": ">", "nt_bp": 50},
        "legacy_midpoint": "int((raw_QueryStart+raw_QueryEnd)/2)",
        "cluster_distance": 15,
        "coordinate_mapping_table_sha256": coordinate_mapping_sha,
        "primary_endpoint": "score_complete_set_success_rate",
        "confidence_method": "one_sided_exact_clopper_pearson",
        "alpha": 0.05,
        "lcb_min": 0.95,
        "double_empty": "non_informative_not_success",
        "strict_row_equality": "diagnostic_only",
        "clustering": {
            "algorithm": "exact_legacy_cluster_triplex",
            "distance": 15,
            "minimum_nt_rule": "strict_greater_than",
            "minimum_nt_bp": 50,
            "midpoint_formula": "(raw_QueryStart+raw_QueryEnd)//2",
            "max_tie_comparison": "strict_greater_than",
            "dynamic_map_operator_indexing": True,
            "fixture_sha256": cluster_sha,
        },
        "input_identity": {
            "logic": "AND",
            "fields": list(contract.INPUT_IDENTITY_FIELDS),
            "ordinal_identity": "namespace_and_ordinal",
            "mismatch_behavior": "technical_failure_matching_not_started_all_primary_metrics_fail",
            "pair_digest_serialization": "UTF-8_sorted_keys_compact_JSON_SHA-256",
        },
        "coordinates": {
            "canonical_basis": "0_based_half_open_forward_target",
            "query_raw_basis": "1_based_inclusive",
            "reachable_directions": ["R"],
            "unreachable_directions": ["L"],
            "fixture_sha256": coordinate_sha,
        },
        "exact_numbers": {
            "decimal_regex": contract.DECIMAL_PATTERN.pattern,
            "score_representation": "integral_exact",
            "score_decimal_string_required": True,
            "score_integer_required": True,
            "nt_representation": "exact_integer",
            "stability_representation": "exact_Decimal",
            "identity_representation": "exact_Decimal",
            "binary_float_contract_comparison": False,
        },
        "ranking": {
            "score": ["Score_desc", "Nt_desc", "MeanStability_desc", "full_row_desc_within_arm_only"],
            "stability": ["MeanStability_desc", "Nt_desc", "Score_desc", "full_row_desc_within_arm_only"],
            "nt": ["Nt_desc", "Score_desc", "MeanStability_desc", "full_row_desc_within_arm_only"],
            "full_row_fallback_cross_arm_identity": False,
        },
        "matching": {
            "input_identity": "all_fields_AND",
            "objective": "lexicographic_aggregate_exact_fraction",
            "equivalent_optima": "failure",
            "query_representative_reciprocal_overlap_min": {"numerator": 9, "denominator": 10},
            "query_cluster_span_reciprocal_overlap_min": {"numerator": 9, "denominator": 10},
            "target_representative_reciprocal_overlap_min": {"numerator": 9, "denominator": 10},
            "overlap_definition": "intersection_length/max(length_A,length_G)",
            "arithmetic": "exact_Fraction_and_integer_cross_multiplication",
            "one_to_one_objective": [
                "matched_edge_count_max",
                "sum_target_overlap_max",
                "sum_query_rep_overlap_max",
                "sum_query_cluster_overlap_max",
                "sum_ungapped_tfo_equal_max",
                "sum_ungapped_tts_equal_max",
                "sum_target_endpoint_L1_min",
                "sum_query_endpoint_L1_min",
                "sum_cluster_center_distance_min",
            ],
            "objective_comparison": "lexicographic",
            "equal_objective_distinct_pair_sets": "ambiguous_failure",
            "prohibited_tiebreakers": ["score", "Nt", "stability", "cluster_id", "row_order", "backend"],
        },
        "denominator": {
            "only_exclusion": "clean_double_empty",
            "technical_failure": "denominator_eligible_binary_zero",
            "A_nonempty_G_empty": "informative_denominator_eligible_binary_zero",
            "A_empty_G_nonempty": "noninformative_denominator_eligible_binary_zero",
            "clean_double_empty_binary_success": None,
        },
        "statistics": {
            "primary": "score_ranked_complete_set_binary_success_rate",
            "confidence": "one_sided_exact_Clopper_Pearson_95",
            "promotion_lcb": "0.95",
            "n_binary_required": power["n_binary_required"],
            "ordered_diagnostic": {
                "name": "finite_RBO_EXT",
                "depth": 5,
                "p": "0.90",
                "empty_value": "0",
                "claim_role": "secondary_diagnostic_only",
            },
            "zero_failure_hard_gate": [
                "technical_failure_count",
                "missing_output_count",
                "input_identity_mismatch_count",
                "ambiguous_matching_count",
                "unexpected_fallback_count",
            ],
        },
        "operating_envelope_sha256": sha256_bytes(canonical_json_bytes(envelope)),
        "parameter_bundle_sha256": envelope["parameter_bundle_sha256"],
    }


def build() -> dict[Path, bytes]:
    contract = load_contract()
    cluster_bytes = render_tsv(CLUSTER_FIELDS, cluster_fixture_rows(contract))
    coordinate_bytes = render_tsv(COORDINATE_FIELDS, coordinate_fixture_rows(contract))
    coordinate_mapping_bytes = render_tsv(
        COORDINATE_MAPPING_FIELDS,
        coordinate_mapping_rows(),
    )
    audit_rows = score_audit_rows(contract)
    audit_bytes = render_tsv(SCORE_FIELDS, audit_rows)
    if any(row["all_integral"] != 1 for row in audit_rows):
        raise ValueError("a supported score path contains a nonintegral Score")
    score_decision = {
        "schema_version": 1,
        "decision": "integral_exact",
        "normative_product_field": "score_decimal_string",
        "derived_field": "score_integer_required",
        "decimal_exact_fallback": "required_if_any_future_supported_path_is_nonintegral",
        "audit_path": SCORE_AUDIT.relative_to(ROOT).as_posix(),
        "audit_sha256": sha256_bytes(audit_bytes),
        "supported_path_count": len(audit_rows),
        "supported_row_count": sum(int(row["row_count"]) for row in audit_rows),
        "nonintegral_row_count": 0,
        "source_type": "triplex.score_float",
        "assignment_proof": "alignment.sw_score_int_to_float",
        "assignment_source": "fasim/fastsim.h:3714-3724",
        "maximum_query_length": 2812,
        "maximum_match_score_bound": 14060,
        "float_exact_integer_limit": 16777216,
        "bound_pass": True,
    }
    power = build_power_plan(contract)
    envelope = operating_envelope(contract)
    experiment = experimental_plan()
    spec = contract_spec(
        contract,
        cluster_sha=sha256_bytes(cluster_bytes),
        coordinate_sha=sha256_bytes(coordinate_bytes),
        coordinate_mapping_sha=sha256_bytes(coordinate_mapping_bytes),
        envelope=envelope,
        power=power,
    )
    return {
        CLUSTER_FIXTURES: cluster_bytes,
        COORDINATE_FIXTURES: coordinate_bytes,
        COORDINATE_MAPPING_TABLE: coordinate_mapping_bytes,
        SCORE_AUDIT: audit_bytes,
        SCORE_DECISION: canonical_json_bytes(score_decision),
        POWER_PLAN: canonical_json_bytes(power),
        EXPERIMENTAL_PLAN: canonical_json_bytes(experiment),
        ENVELOPE_PATH: canonical_json_bytes(envelope),
        CONTRACT_SPEC: canonical_json_bytes(spec),
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
                print(f"contract artifact drift: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("biological Top-K contract artifacts reproduce byte-for-byte")
        return 0
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(outputs)} Phase 1 contract artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
