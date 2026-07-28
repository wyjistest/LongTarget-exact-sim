#!/usr/bin/env python3
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


COMPARATOR = load_module("ssw_cuda_layered_comparator", ROOT / "reproduce/ssw_cuda/compare_layers.py")
CORPUS = load_module("ssw_cuda_phase3_corpus", ROOT / "reproduce/ssw_cuda/build_corpus.py")


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def mismatch_rows() -> list[dict[str, str]]:
    with (ROOT / "paper/bioinformatics/holdout_mismatch_details.tsv").open(
        newline="", encoding="utf-8"
    ) as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def canonical_row(row: dict[str, str]) -> dict[str, str]:
    excluded = {"attempt_id", "workload_id", "evidence_kind", "side", "kind", "mode", "rank"}
    return {key: value for key, value in row.items() if key not in excluded}


def ranked_rows(attempt_id: str, side: str, mode: str) -> list[dict[str, str]]:
    selected = [
        row
        for row in mismatch_rows()
        if row["attempt_id"] == attempt_id
        and row["side"] == side
        and row["kind"] == "clustered"
        and row["mode"] == mode
    ]
    return [canonical_row(row) for row in sorted(selected, key=lambda row: int(row["rank"]))]


def affected_full_rows(attempt_id: str, side: str) -> list[str]:
    evidence_kind = "full_missing" if side == "baseline" else "full_extra"
    selected = [
        canonical_row(row)
        for row in mismatch_rows()
        if row["attempt_id"] == attempt_id
        and row["side"] == side
        and row["evidence_kind"] == evidence_kind
    ]
    return [
        hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for row in selected
    ]


def cigar_from_aligned_row(row: dict[str, str]) -> str:
    tfo = row["TFO sequence"]
    tts = row["TTS sequence"]
    if len(tfo) != len(tts):
        raise RuntimeError("aligned historical row length mismatch")
    operations: list[list[object]] = []
    for query_base, reference_base in zip(tfo, tts):
        if query_base == "-":
            operation = "D"
        elif reference_base == "-":
            operation = "I"
        else:
            operation = "M"
        if operations and operations[-1][1] == operation:
            operations[-1][0] = int(operations[-1][0]) + 1
        else:
            operations.append([1, operation])
    return "".join(f"{length}{operation}" for length, operation in operations)


def known_mismatch_bundles(case: str):
    if case == "hq10":
        attempt_id = "hq10_ht02__repeat00"
        prealign = read_json("tests/ssw_cuda/fixtures/hq10_prealign.json")
        alignment = read_json("tests/ssw_cuda/fixtures/hq10_mismatch_call.json")
        mismatch_mode = "stability"
        mismatch_rank = "1"
    elif case == "hq11":
        attempt_id = "hq11_ht02__repeat00"
        prealign = read_json("tests/ssw_cuda/fixtures/hq11_prealign.json")
        alignment = read_json("tests/ssw_cuda/fixtures/hq11_mismatch_call.json")
        mismatch_mode = "score"
        mismatch_rank = "3"
    else:
        raise RuntimeError(f"unknown case: {case}")

    shared = {
        "schema_version": "1",
        "case_id": attempt_id,
        "prealign": prealign,
        "alignment": alignment,
        "clustered_top5": {
            "score": ranked_rows(attempt_id, "baseline", "score") or ["historically_equal_score"],
            "stability": ranked_rows(attempt_id, "baseline", "stability")
            or ["historically_equal_stability"],
            "Nt": ["historically_equal_Nt"],
        },
        "full_output_row_digests": affected_full_rows(attempt_id, "baseline"),
    }
    authority = copy.deepcopy(shared)
    candidate = copy.deepcopy(shared)
    candidate_rows = ranked_rows(attempt_id, "candidate", mismatch_mode)
    candidate["clustered_top5"][mismatch_mode] = candidate_rows
    candidate["full_output_row_digests"] = affected_full_rows(attempt_id, "candidate")
    mismatch_row = next(row for row in candidate_rows if row["cluster_id"] == "2")
    candidate["alignment"]["traceback"]["cigar"] = cigar_from_aligned_row(mismatch_row)
    candidate["alignment"]["emitted_rows"] = [mismatch_row]
    if case == "hq11":
        target_start = candidate["alignment"]["attempt"]["target_start"]
        candidate["alignment"]["reverse_start"] = {
            "ref_begin1": int(mismatch_row["StartInSeq"]) - target_start - 1,
            "read_begin1": int(mismatch_row["QueryStart"]) - 1,
        }
    return authority, candidate, mismatch_rank


def fresh_candidate(candidate_id: str = "fresh-1") -> dict[str, object]:
    identity = {
        "query_ordinal_namespace": "future_source_v1",
        "query_source_ordinal": "9001",
        "target_ordinal_namespace": "future_source_v1",
        "target_source_ordinal": "9002",
        "query_id": "future_query",
        "target_id": "future_target",
        "query_sha256": hashlib.sha256(b"never-used-query").hexdigest(),
        "target_sha256": hashlib.sha256(b"never-used-target").hexdigest(),
        "query_region": "full",
        "target_region": "full",
    }
    return {
        "candidate_id": candidate_id,
        **identity,
        "pair_digest": CORPUS.exclusion_pair_digest(identity),
        "source_receipt_path": "paper/ssw_cuda/future_holdout_population.tsv",
        "usage_tags": ["fresh_candidate"],
    }


def rebind(candidate: dict[str, object]) -> None:
    identity_fields = (
        "query_ordinal_namespace",
        "query_source_ordinal",
        "target_ordinal_namespace",
        "target_source_ordinal",
        "query_id",
        "target_id",
        "query_sha256",
        "target_sha256",
        "query_region",
        "target_region",
    )
    candidate["pair_digest"] = CORPUS.exclusion_pair_digest(
        {field: str(candidate[field]) for field in identity_fields}
    )


class LayeredComparatorTests(unittest.TestCase):
    def test_identical_bundle_has_no_divergence(self) -> None:
        authority, _, _ = known_mismatch_bundles("hq10")
        result = COMPARATOR.compare_layers(authority, copy.deepcopy(authority))
        self.assertIsNone(result["first_divergent_layer"])
        self.assertTrue(result["L7_score_stability_Nt_top5_equal"])
        self.assertTrue(result["L8_full_output_diagnostic_equal"])
        self.assertEqual(result["L8_contract_status"], "diagnostic_only")

    def test_l1_reports_exact_first_column(self) -> None:
        authority, _, _ = known_mismatch_bundles("hq10")
        candidate = copy.deepcopy(authority)
        final_path = candidate["prealign"]["final_numeric_path"]
        final_pass = next(
            row
            for row in candidate["prealign"]["dp_passes"]
            if row["numeric_path"] == final_path
        )
        final_pass["columns"][17] += 1
        final_pass["column_max_digest_fnv1a64"] = "0000000000000000"
        result = COMPARATOR.compare_layers(authority, candidate)
        self.assertFalse(result["L1_column_equal"])
        self.assertEqual(result["L1_first_diff_column"], 17)
        self.assertEqual(result["first_divergent_layer"], "L1")

    def test_l2_reports_false_negative_extra_and_order(self) -> None:
        authority, _, _ = known_mismatch_bundles("hq10")
        candidate = copy.deepcopy(authority)
        scoreinfos = candidate["prealign"]["selection"]["scoreinfos"]
        removed = scoreinfos.pop(0)
        scoreinfos.append({"index": 999, "position": 2499, "score": 999})
        result = COMPARATOR.compare_layers(authority, candidate)
        self.assertFalse(result["L2_selection_equal"])
        self.assertEqual(result["L2_false_negative"], [removed])
        self.assertEqual(result["L2_extra"][0]["index"], 999)
        self.assertFalse(result["L2_order_equal"])
        self.assertEqual(result["first_divergent_layer"], "L2")

    def test_known_hq10_is_first_l5_gap_placement_divergence(self) -> None:
        authority, candidate, _ = known_mismatch_bundles("hq10")
        result = COMPARATOR.compare_layers(authority, candidate)
        for layer in ("L0_input_equal", "L1_column_equal", "L2_selection_equal", "L3_forward_equal", "L4_reverse_equal"):
            self.assertTrue(result[layer], layer)
        self.assertEqual(authority["alignment"]["traceback"]["cigar"], "20M1I4M2D31M")
        self.assertEqual(candidate["alignment"]["traceback"]["cigar"], "20M2D4M1I31M")
        self.assertFalse(result["L5_cigar_equal"])
        self.assertEqual(result["L5_first_diff_op"], 1)
        self.assertEqual(result["first_divergent_layer"], "L5")
        self.assertTrue(result["L7_score_top5_equal"])
        self.assertFalse(result["L7_stability_top5_equal"])
        self.assertTrue(result["L7_Nt_top5_equal"])
        self.assertFalse(result["L8_full_output_diagnostic_equal"])

    def test_known_hq11_is_first_l4_reverse_start_divergence(self) -> None:
        authority, candidate, _ = known_mismatch_bundles("hq11")
        result = COMPARATOR.compare_layers(authority, candidate)
        for layer in ("L0_input_equal", "L1_column_equal", "L2_selection_equal", "L3_forward_equal"):
            self.assertTrue(result[layer], layer)
        self.assertEqual(authority["alignment"]["reverse_start"]["ref_begin1"], 22)
        self.assertEqual(candidate["alignment"]["reverse_start"]["ref_begin1"], 19)
        self.assertEqual(candidate["alignment"]["traceback"]["cigar"], "13M1I52M")
        self.assertFalse(result["L4_reverse_equal"])
        self.assertEqual(result["first_divergent_layer"], "L4")
        self.assertFalse(result["L7_score_top5_equal"])
        self.assertTrue(result["L7_stability_top5_equal"])
        self.assertTrue(result["L7_Nt_top5_equal"])
        self.assertFalse(result["L8_full_output_diagnostic_equal"])


class CorpusFreezeTests(unittest.TestCase):
    def test_corpus_counts_and_required_partitions_are_deterministic(self) -> None:
        rows = CORPUS.build_manifest_rows()
        partitions = {row["corpus_partition"] for row in rows}
        self.assertEqual(
            partitions,
            {"historical_regression", "tiny_exhaustive", "adversarial", "deterministic_fuzz"},
        )
        self.assertEqual(sum(row["corpus_partition"] == "tiny_exhaustive" for row in rows), 196)
        self.assertEqual(
            sum(row["case_id"].startswith("fuzz-compact-") for row in rows),
            CORPUS.COMPACT_FUZZ_COUNT,
        )
        self.assertEqual(
            sum(row["case_id"].startswith("fuzz-large-") for row in rows),
            CORPUS.LARGE_FUZZ_COUNT,
        )
        self.assertTrue(all(row["holdout_eligible"] == 0 for row in rows))

    def test_registry_is_rebuilt_and_fully_represented(self) -> None:
        rebuilt = CORPUS.rebuild_registry()
        rows = CORPUS.build_manifest_rows()
        coverage = CORPUS.registry_coverage(rows, CORPUS.load_registry())
        self.assertEqual(len(rebuilt), 112)
        self.assertEqual(coverage["registry_rows"], 112)
        self.assertEqual(coverage["manifest_identity_rows"], 112)
        self.assertTrue(coverage["all_registry_rows_represented"])

    def test_adversarial_contract_is_complete(self) -> None:
        rows = CORPUS.adversarial_rows()
        classes = {row["case_class"] for row in rows}
        self.assertTrue(CORPUS.REQUIRED_ADVERSARIAL_CLASSES <= classes)
        scores = {
            int(row["expected_max_score"])
            for row in rows
            if row["case_class"].startswith("byte_boundary_")
        }
        self.assertEqual(scores, {253, 254, 255, 256})
        self.assertEqual(
            {int(row["query_length"]) for row in rows if row["case_class"] == "length_boundary"},
            set(CORPUS.LENGTH_BOUNDARIES),
        )

    def test_large_cases_are_never_normal_checker_work(self) -> None:
        rows = CORPUS.build_manifest_rows()
        large = [row for row in rows if row["execution_tier"] == "large"]
        self.assertTrue(large)
        self.assertTrue(all(row["expected_property"] for row in large))
        policy = (ROOT / "docs/ssw_cuda/HOLDOUT_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("explicit expensive gate only", policy)
        self.assertIn("does not execute historical workloads or the", policy)


class HoldoutPolicyTests(unittest.TestCase):
    def test_synthetic_fresh_identity_passes(self) -> None:
        result = CORPUS.validate_holdout_candidates([fresh_candidate()])
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["overlap_count"], 0)

    def test_query_digest_overlap_fails_closed(self) -> None:
        candidate = fresh_candidate()
        registry_row = CORPUS.load_registry()[0]
        candidate["query_sha256"] = registry_row["query_sha256"]
        rebind(candidate)
        with self.assertRaisesRegex(CORPUS.HoldoutOverlapError, "query_sequence_digest_overlap"):
            CORPUS.validate_holdout_candidates([candidate])

    def test_target_ordinal_overlap_fails_closed(self) -> None:
        candidate = fresh_candidate()
        registry_row = next(
            row for row in CORPUS.load_registry() if row["target_source_ordinal"] != "NA"
        )
        candidate["target_ordinal_namespace"] = registry_row["target_ordinal_namespace"]
        candidate["target_source_ordinal"] = registry_row["target_source_ordinal"]
        rebind(candidate)
        with self.assertRaisesRegex(CORPUS.HoldoutOverlapError, "target_source_ordinal_overlap"):
            CORPUS.validate_holdout_candidates([candidate])

    def test_pair_and_receipt_overlap_fail_closed(self) -> None:
        row = next(
            item
            for item in CORPUS.load_registry()
            if item["record_type"] == "pair"
            and item["query_source_ordinal"] != "NA"
            and item["target_source_ordinal"] != "NA"
        )
        candidate = fresh_candidate()
        for field in (
            "query_ordinal_namespace",
            "query_source_ordinal",
            "target_ordinal_namespace",
            "target_source_ordinal",
            "query_id",
            "target_id",
            "query_sha256",
            "target_sha256",
            "query_region",
            "target_region",
            "pair_digest",
        ):
            candidate[field] = row[field]
        candidate["source_receipt_path"] = row["source_receipt_path"].split(";")[0]
        with self.assertRaisesRegex(CORPUS.HoldoutOverlapError, "pair_digest_overlap"):
            CORPUS.validate_holdout_candidates([candidate])

    def test_debug_or_missing_identity_fails_closed(self) -> None:
        candidate = fresh_candidate()
        candidate["usage_tags"] = ["debug"]
        with self.assertRaisesRegex(CORPUS.HoldoutOverlapError, "prior_use:debug"):
            CORPUS.validate_holdout_candidates([candidate])
        del candidate["query_region"]
        with self.assertRaisesRegex(CORPUS.CorpusError, "missing fields"):
            CORPUS.validate_holdout_candidates([candidate])


if __name__ == "__main__":
    unittest.main()
