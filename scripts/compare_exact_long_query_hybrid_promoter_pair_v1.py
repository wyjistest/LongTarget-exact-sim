#!/usr/bin/env python3
"""Compare one paired CPU/exact-hybrid real-promoter validation workload."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Mapping

import gasal2_candidate_sites as candidate_sites
from decode_exact_long_query_hybrid_promoter_case_v1 import decode_case, sole_output
from exact_long_query_promoter_mapping import PromoterMapping, read_single_fasta, sha256_file


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs/exact_long_query_hybrid_promoter_panel_v1"
AFFINITY_BUILDER = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/build_dbd1_promoter_affinity.py"
)
AFFINITY_BUILDER_SHA256 = "67bd6f2959f45c0cf3c76ed8c51379e49a794a0cffb720bfe820a800ad216e41"
BOUNDARY_RECEIPT = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_promoter_panel_v1/boundary_fixtures/receipt.json"
)
MAPPER_SHA256 = "f784367f9108a4e6641cffaf041069ef1c469961f431795cd0d04d97eff37925"
DECODE_ARTIFACTS = (
    "decoded-TFOsorted.tsv.zst",
    "mapped_promoter_associations.tsv.zst",
    "rejected_hits.tsv.zst",
    "retained-TFOsorted",
)
AFFINITY_ARTIFACTS = (
    "dbd1.tsv",
    "strong_dbs.tsv.zst",
    "lncrna_promoter_pairs.tsv.zst",
    "lncrna_target_gene_pairs.tsv.zst",
)


class PairError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PairError(message)


def files_byte_equal(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_handle, right.open("rb") as right_handle:
        while True:
            left_block = left_handle.read(8 * 1024 * 1024)
            right_block = right_handle.read(8 * 1024 * 1024)
            if left_block != right_block:
                return False
            if not left_block:
                return True


def exact_artifact(left: Path, right: Path, label: str) -> dict[str, object]:
    require(left.is_file() and right.is_file(), f"missing {label} artifact")
    require(files_byte_equal(left, right), f"{label} is not byte-identical")
    digest = sha256_file(left)
    require(digest == sha256_file(right), f"{label} digest mismatch")
    return {"status": "byte_identical", "bytes": left.stat().st_size, "sha256": digest}


def load_case_receipt(path: Path, expected_arm: str) -> dict[str, object]:
    receipt_path = path / "receipt.json"
    require(receipt_path.is_file(), f"missing case receipt: {path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(
        receipt.get("status") == "complete"
        and receipt.get("technical_contract_pass") is True
        and receipt.get("arm") == expected_arm,
        f"incomplete {expected_arm} case receipt",
    )
    if expected_arm == "candidate":
        require(receipt.get("backend") == "exact_long_query_hybrid", "candidate backend mismatch")
        consumer = receipt.get("consumer")
        require(isinstance(consumer, dict), "candidate consumer receipt missing")
        require(
            int(consumer["attempts"]) == int(consumer["gpu_scored_attempts"])
            and int(consumer["cpu_oracle_attempts"]) == 0
            and int(consumer["cpu_reference_align_attempts"]) == 0
            and int(consumer["cpu_continuation_failures"]) == 0,
            "candidate GPU/CPU accounting gate failed",
        )
    return receipt


def validate_pair_identity(baseline: Mapping[str, object], candidate: Mapping[str, object]) -> None:
    require(baseline["workload_id"] == candidate["workload_id"], "paired workload ID mismatch")
    require(baseline["stage"] == candidate["stage"], "paired stage mismatch")
    for section in ("binary", "query", "target"):
        require(baseline[section] == candidate[section], f"paired {section} identity mismatch")


def validate_boundary_gate(promoter_root: Path) -> dict[str, object]:
    require(BOUNDARY_RECEIPT.is_file(), "boundary fixture receipt missing")
    receipt = json.loads(BOUNDARY_RECEIPT.read_text(encoding="utf-8"))
    require(receipt.get("status") == "boundary_fixture_gate_pass", "boundary fixture gate did not pass")
    require(receipt.get("fixture_count") == 7, "boundary fixture count mismatch")
    require(receipt.get("mapper_sha256") == MAPPER_SHA256, "boundary receipt mapper identity mismatch")
    mapper = ROOT / "scripts/exact_long_query_promoter_mapping.py"
    require(sha256_file(mapper) == MAPPER_SHA256, "promoter mapper changed after boundary receipt")
    require(receipt.get("promoter_root") == str(promoter_root), "boundary promoter root mismatch")
    require(receipt.get("positive_cross_component_control_exercised") is True, "cross-component control missing")
    require(receipt.get("positive_reference_n_control_exercised") is True, "reference-N control missing")
    return {
        "status": "pass",
        "receipt": str(BOUNDARY_RECEIPT),
        "receipt_sha256": sha256_file(BOUNDARY_RECEIPT),
        "fixture_count": 7,
        "mapper_sha256": MAPPER_SHA256,
    }


def run_affinity_builder(
    decode_root: Path,
    output_root: Path,
    promoter_root: Path,
    gene_id: str,
    log_root: Path,
    arm: str,
) -> dict[str, object]:
    require(AFFINITY_BUILDER.is_file(), "frozen affinity builder missing")
    require(sha256_file(AFFINITY_BUILDER) == AFFINITY_BUILDER_SHA256, "affinity builder digest drift")
    command = [
        os.sys.executable,
        str(AFFINITY_BUILDER),
        "--decode-root",
        str(decode_root),
        "--output-root",
        str(output_root),
        "--promoter-root",
        str(promoter_root),
        "--job",
        gene_id,
        "--affinity-threshold",
        "0",
        "--sort-memory",
        "1G",
        "--sort-parallel",
        "1",
    ]
    stdout_path = log_root / f"affinity-{arm}.stdout.log"
    stderr_path = log_root / f"affinity-{arm}.stderr.log"
    started = time.perf_counter()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr)
    require(completed.returncode == 0, f"{arm} affinity builder failed: {stderr_path}")
    receipt_path = output_root / gene_id / "receipt.json"
    require(receipt_path.is_file(), f"{arm} affinity receipt missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("status") == "complete", f"{arm} affinity receipt incomplete")
    require(receipt.get("rules", {}).get("binding_affinity_threshold") == "0.000000", "affinity threshold drift")
    return {
        "command": command,
        "wall_seconds": time.perf_counter() - started,
        "receipt": str(receipt_path.resolve()),
        "receipt_sha256": sha256_file(receipt_path),
        "counts": receipt["counts"],
        "selected_dbd1": receipt["selected_dbd1"],
    }


def write_candidate_sites_allow_reference_n(
    query_fasta: Path,
    target_fasta: Path,
    tfosorted: Path,
    destination: Path,
    workload_id: str,
    gene_id: str,
) -> dict[str, object]:
    query_header, query_sequence = read_single_fasta(query_fasta)
    target_header, target_sequence = read_single_fasta(target_fasta)
    query = candidate_sites.FastaRecord(query_fasta.resolve(), query_header, query_sequence)
    target = candidate_sites.FastaRecord(target_fasta.resolve(), target_header, target_sequence)
    identity = candidate_sites.ProductIdentity(
        workload_id=workload_id,
        query_ordinal_namespace="gencode_v33_gene_id_v1",
        query_source_ordinal=gene_id,
        target_ordinal_namespace="genes20cells_promoter_concat_v1",
        target_source_ordinal="logical_full_concat",
        assembly="GRCh38",
        target_coordinate_namespace="promoter_components_concat_0_based_half_open_v1",
    )
    receipt = candidate_sites.build_receipt(
        query=query,
        target=target,
        tfosorted=tfosorted,
        identity=identity,
    )
    validated = candidate_sites.canonicalize_rows.validate_receipt_files(receipt, tfosorted)
    rows = candidate_sites.canonicalize_rows.canonicalize_output(tfosorted, validated)
    rankings = candidate_sites.recluster_candidate_sites.all_rankings(
        rows,
        receipt,
        k=5,
        distance=15,
        minimum_nt_bp=50,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=candidate_sites.FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for mode in candidate_sites.RANKING_ORDER:
            for site in rankings[mode]:
                writer.writerow(candidate_sites._product_row(site))
    summary = candidate_sites.validate_candidate_sites(destination)
    summary.update({
        "input_pair_digest": receipt.input_identity["input_pair_digest"],
        "workload_id": receipt.workload_id,
        "native_output_sha256": receipt.output_sha256,
        "reference_n_policy": "input_N_allowed_only_after_decoder_rejected_every_overlapping_hit",
    })
    return summary


def run_pair(
    baseline_root: Path,
    candidate_root: Path,
    output_root: Path,
    promoter_root: Path,
) -> dict[str, object]:
    require(not output_root.exists(), f"refusing to overwrite pair output: {output_root}")
    baseline = load_case_receipt(baseline_root, "baseline")
    candidate = load_case_receipt(candidate_root, "candidate")
    validate_pair_identity(baseline, candidate)
    output_root.mkdir(parents=True)
    boundary = validate_boundary_gate(promoter_root)
    baseline_raw = sole_output(baseline_root, baseline)
    candidate_raw = sole_output(candidate_root, candidate)
    raw_comparison = exact_artifact(baseline_raw, candidate_raw, "raw complete TFOsorted")

    gene_id = str(dict(baseline["query"])["gene_id"])
    workload_id = str(baseline["workload_id"])
    decode_roots = {
        "baseline": output_root / "decode" / "baseline" / gene_id,
        "candidate": output_root / "decode" / "candidate" / gene_id,
    }
    decode_summaries = {
        "baseline": decode_case(baseline_root, decode_roots["baseline"], promoter_root),
        "candidate": decode_case(candidate_root, decode_roots["candidate"], promoter_root),
    }
    require(
        decode_summaries["baseline"]["rejection_reason_counts"]
        == decode_summaries["candidate"]["rejection_reason_counts"],
        "decode rejection counts differ",
    )
    decode_comparisons = {
        name: exact_artifact(
            decode_roots["baseline"] / name,
            decode_roots["candidate"] / name,
            f"decoded {name}",
        )
        for name in DECODE_ARTIFACTS
    }

    affinity_roots = {
        "baseline": output_root / "affinity" / "baseline",
        "candidate": output_root / "affinity" / "candidate",
    }
    affinity_runs = {
        arm: run_affinity_builder(
            decode_roots[arm].parent,
            affinity_roots[arm],
            promoter_root,
            gene_id,
            output_root,
            arm,
        )
        for arm in ("baseline", "candidate")
    }
    require(affinity_runs["baseline"]["counts"] == affinity_runs["candidate"]["counts"], "affinity counts differ")
    require(
        affinity_runs["baseline"]["selected_dbd1"] == affinity_runs["candidate"]["selected_dbd1"],
        "selected DBD1 differs",
    )
    affinity_comparisons = {
        name: exact_artifact(
            affinity_roots["baseline"] / gene_id / name,
            affinity_roots["candidate"] / gene_id / name,
            f"affinity {name}",
        )
        for name in AFFINITY_ARTIFACTS
    }

    mapping = PromoterMapping(promoter_root)
    full_target = mapping.target_context("logical_full_concat")
    query_path = Path(str(dict(baseline["query"])["path"]))
    candidate_site_summaries = {
        arm: write_candidate_sites_allow_reference_n(
            query_path,
            full_target.path,
            decode_roots[arm] / "retained-TFOsorted",
            output_root / "candidate_sites" / f"{arm}.tsv",
            workload_id,
            gene_id,
        )
        for arm in ("baseline", "candidate")
    }
    candidate_site_comparison = exact_artifact(
        output_root / "candidate_sites" / "baseline.tsv",
        output_root / "candidate_sites" / "candidate.tsv",
        "biological_topk_candidate_site_v1",
    )
    require(
        candidate_site_summaries["baseline"]["row_count"]
        == candidate_site_summaries["candidate"]["row_count"],
        "candidate-site row counts differ",
    )

    receipt = {
        "schema_version": "exact_long_query_hybrid_promoter_pair_receipt_v1",
        "status": "pair_gate_pass",
        "workload_id": workload_id,
        "gene_id": gene_id,
        "baseline_case": str(baseline_root.resolve()),
        "candidate_case": str(candidate_root.resolve()),
        "raw_tfosorted": raw_comparison,
        "boundary_fixture_gate": boundary,
        "decode": {
            "baseline_summary": decode_summaries["baseline"],
            "candidate_summary": decode_summaries["candidate"],
            "exact_artifacts": decode_comparisons,
        },
        "dbd_dbs_affinity_threshold_zero": {
            "builder": str(AFFINITY_BUILDER),
            "builder_sha256": AFFINITY_BUILDER_SHA256,
            "baseline": affinity_runs["baseline"],
            "candidate": affinity_runs["candidate"],
            "exact_artifacts": affinity_comparisons,
        },
        "biological_topk_candidate_site_v1": {
            "baseline": candidate_site_summaries["baseline"],
            "candidate": candidate_site_summaries["candidate"],
            "exact_artifact": candidate_site_comparison,
        },
        "gates": {
            "raw_tfosorted_byte_identical": True,
            "coordinate_mapping_exact": True,
            "rejection_taxonomy_exact": True,
            "dbd1_exact": True,
            "dbs_peak_set_exact": True,
            "binding_affinity_exact_at_threshold_zero": True,
            "candidate_site_exact": True,
            "candidate_gpu_accounting_pass": True,
        },
    }
    (output_root / "pair-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--baseline-root", type=Path, required=True)
    result.add_argument("--candidate-root", type=Path, required=True)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--promoter-root", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    result = run_pair(args.baseline_root, args.candidate_root, args.output_root, args.promoter_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        PairError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
        candidate_sites.CandidateSitesError,
    ) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(2)
