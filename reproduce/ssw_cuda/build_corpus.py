#!/usr/bin/env python3
"""Build and validate the frozen Phase 3 SSW-CUDA differential corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "paper/ssw_cuda/corpus_manifest.tsv"
MANIFEST_CHECKSUM = ROOT / "paper/ssw_cuda/corpus_manifest.sha256"
RECEIPT = ROOT / "paper/ssw_cuda/corpus_receipt.json"
REGISTRY = ROOT / "paper/ssw_cuda/used_input_exclusion_registry.tsv"
REGISTRY_CHECKSUM = ROOT / "paper/ssw_cuda/used_input_exclusion_registry.sha256"
POLICY = ROOT / "docs/ssw_cuda/HOLDOUT_POLICY.md"
COMPARATOR = ROOT / "reproduce/ssw_cuda/compare_layers.py"
PHASE0_FREEZER = ROOT / "reproduce/ssw_cuda/freeze_phase0.py"

SCHEMA_VERSION = "1"
GENERATOR_VERSION = "ssw-cuda-corpus-v1"
CORPUS_PAIR_SCHEMA = "ssw-cuda-corpus-pair-v1"
EXCLUSION_PAIR_SCHEMA = "ssw-cuda-exclusion-pair-v1"
COMPACT_FUZZ_SEED = 0x5353574355444131
LARGE_FUZZ_SEED = 0x5353574355444132
COMPACT_FUZZ_COUNT = 128
LARGE_FUZZ_COUNT = 256
MASK64 = (1 << 64) - 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

MANIFEST_FIELDS = (
    "case_id",
    "corpus_partition",
    "case_class",
    "execution_tier",
    "source_kind",
    "source_path",
    "source_key",
    "sequence_encoding",
    "alphabet",
    "query_length",
    "reference_length",
    "query_sha256",
    "reference_sha256",
    "pair_digest_schema",
    "pair_digest",
    "generator",
    "seed",
    "generator_parameters_json",
    "expected_max_score",
    "expected_property",
    "contract_layers",
    "holdout_eligible",
)

REQUIRED_EXCLUSION_REASONS = {
    "historical_development_or_paper_workload",
    "historical_development_query",
    "phase2_fixed_pilot",
    "phase2_correctness_holdout",
    "phase2_traceback_replay",
    "phase3_v1_fixed_pilot",
    "canonical_hybrid_v2_regression",
    "canonical_hybrid_v2_fresh_holdout",
    "canonical_hybrid_v2_performance_pilot",
}

REQUIRED_ADVERSARIAL_CLASSES = {
    "homopolymer",
    "periodic_repeat",
    "palindrome_reverse_complement",
    "equal_forward_endpoints",
    "equal_reverse_starts",
    "equal_gap_placements",
    "open_extend_tie",
    "e_f_tie",
    "diagonal_gap_tie",
    "byte_boundary_253",
    "byte_boundary_254",
    "byte_boundary_255",
    "byte_boundary_256",
    "length_boundary",
    "supported_unknown_n",
    "supported_u_translation",
    "supported_lowercase",
    "unsupported_empty_query",
    "unsupported_empty_reference",
    "unsupported_non_ascii",
    "unsupported_nul",
}

LENGTH_BOUNDARIES = (
    31,
    32,
    33,
    63,
    64,
    65,
    127,
    128,
    129,
    253,
    254,
    255,
    256,
    257,
    511,
    512,
    513,
    1023,
    1024,
    1025,
    2047,
    2048,
    2049,
    2811,
    2812,
)

DISALLOWED_PRIOR_USE_TAGS = {
    "prior_correctness",
    "prior_performance",
    "pilot",
    "debug",
    "minimization",
    "fuzz_replay",
}


class CorpusError(RuntimeError):
    pass


class HoldoutOverlapError(CorpusError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CorpusError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_registry() -> list[dict[str, str]]:
    rows = read_tsv(REGISTRY)
    require(len(rows) == 112, "used-input exclusion registry row-count drift")
    require(len({tuple(row.items()) for row in rows}) == len(rows), "duplicate registry row")
    expected_checksum = REGISTRY_CHECKSUM.read_text(encoding="ascii").split()[0]
    require(sha256_file(REGISTRY) == expected_checksum, "registry checksum drift")
    return rows


def rebuild_registry() -> list[dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("ssw_cuda_phase0_freezer", PHASE0_FREEZER)
    require(spec is not None and spec.loader is not None, "cannot load Phase 0 registry builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    rows = module.build_registry()
    payload = module.tsv_bytes(module.REGISTRY_FIELDS, rows)
    require(payload == REGISTRY.read_bytes(), "used-input exclusion registry is not reproducible")
    return rows


def exclusion_pair_digest(fields: dict[str, str]) -> str:
    payload = {"schema": EXCLUSION_PAIR_SCHEMA, **fields}
    return sha256_bytes(compact_json(payload).encode("utf-8"))


def generated_pair_digest(query: bytes, reference: bytes) -> str:
    payload = {
        "schema": CORPUS_PAIR_SCHEMA,
        "query_length": len(query),
        "query_sha256": sha256_bytes(query),
        "reference_length": len(reference),
        "reference_sha256": sha256_bytes(reference),
        "scoring": {"match": 5, "mismatch_penalty": 4, "gap_open": 16, "gap_extend": 4},
    }
    return sha256_bytes(compact_json(payload).encode("utf-8"))


def smith_waterman_max_score(query: bytes, reference: bytes) -> int:
    """Small scalar diagnostic matching the frozen affine score relation."""
    if not query or not reference:
        return 0
    previous = [0] * (len(reference) + 1)
    vertical = [-(1 << 30)] * (len(reference) + 1)
    best = 0
    for query_base in query:
        current = [0] * (len(reference) + 1)
        horizontal = -(1 << 30)
        for column, reference_base in enumerate(reference, 1):
            horizontal = max(current[column - 1] - 16, horizontal - 4)
            vertical[column] = max(previous[column] - 16, vertical[column] - 4)
            score = max(
                0,
                previous[column - 1] + (5 if query_base == reference_base else -4),
                horizontal,
                vertical[column],
            )
            current[column] = score
            best = max(best, score)
        previous = current
    return best


class SplitMix64:
    def __init__(self, seed: int) -> None:
        self.state = seed & MASK64

    def next(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64

    def randbelow(self, upper_bound: int) -> int:
        require(upper_bound > 0, "randbelow bound must be positive")
        return self.next() % upper_bound


def periodic(pattern: bytes, length: int) -> bytes:
    require(pattern and length >= 0, "invalid periodic sequence request")
    return (pattern * ((length + len(pattern) - 1) // len(pattern)))[:length]


def fuzz_sequence(rng: SplitMix64, length: int, profile: str) -> bytes:
    require(length > 0, "fuzz sequences must be nonempty")
    if profile == "uniform":
        alphabet = b"ACGT"
        return bytes(alphabet[rng.randbelow(4)] for _ in range(length))
    if profile == "gc_low":
        alphabet = b"AAAATTTTCG"
        return bytes(alphabet[rng.randbelow(len(alphabet))] for _ in range(length))
    if profile == "gc_high":
        alphabet = b"CCCCGGGGAT"
        return bytes(alphabet[rng.randbelow(len(alphabet))] for _ in range(length))
    if profile == "repeat":
        motif_length = 1 + rng.randbelow(8)
        motif = bytes(b"ACGT"[rng.randbelow(4)] for _ in range(motif_length))
        result = bytearray(periodic(motif, length))
        mutation_count = max(1, length // 20)
        for _ in range(mutation_count):
            position = rng.randbelow(length)
            result[position] = b"ACGT"[rng.randbelow(4)]
        return bytes(result)
    raise CorpusError(f"unknown fuzz profile: {profile}")


def generated_row(
    *,
    case_id: str,
    partition: str,
    case_class: str,
    tier: str,
    query: bytes,
    reference: bytes,
    encoding: str,
    alphabet: str,
    generator: str,
    seed: str,
    parameters: dict[str, Any],
    expected_max_score: str | int,
    expected_property: str,
    layers: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "corpus_partition": partition,
        "case_class": case_class,
        "execution_tier": tier,
        "source_kind": "generated",
        "source_path": "reproduce/ssw_cuda/build_corpus.py",
        "source_key": case_id,
        "sequence_encoding": encoding,
        "alphabet": alphabet,
        "query_length": len(query),
        "reference_length": len(reference),
        "query_sha256": sha256_bytes(query),
        "reference_sha256": sha256_bytes(reference),
        "pair_digest_schema": CORPUS_PAIR_SCHEMA,
        "pair_digest": generated_pair_digest(query, reference),
        "generator": generator,
        "seed": seed,
        "generator_parameters_json": compact_json(parameters),
        "expected_max_score": expected_max_score,
        "expected_property": expected_property,
        "contract_layers": layers,
        "holdout_eligible": 0,
    }


def historical_rows(registry: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(registry, 1):
        identity = source["pair_digest"] if source["record_type"] == "pair" else source["query_sha256"]
        rows.append(
            {
                "case_id": f"historical-registry-{index:04d}-{identity[:12]}",
                "corpus_partition": "historical_regression",
                "case_class": f"registry_{source['record_type']}",
                "execution_tier": "identity_only",
                "source_kind": "used_input_exclusion_registry",
                "source_path": source["source_receipt_path"],
                "source_key": identity,
                "sequence_encoding": "historical_identity",
                "alphabet": "as_recorded",
                "query_length": "NA",
                "reference_length": "NA",
                "query_sha256": source["query_sha256"],
                "reference_sha256": source["target_sha256"],
                "pair_digest_schema": EXCLUSION_PAIR_SCHEMA if source["record_type"] == "pair" else "NA",
                "pair_digest": source["pair_digest"],
                "generator": "none",
                "seed": "NA",
                "generator_parameters_json": compact_json(
                    {
                        "query_id": source["query_id"],
                        "target_id": source["target_id"],
                        "exclusion_reason": source["exclusion_reason"],
                    }
                ),
                "expected_max_score": "historical",
                "expected_property": "consumed_input_regression_identity",
                "contract_layers": "L0-L8_as_available",
                "holdout_eligible": 0,
            }
        )

    def add_annotation(case_id: str, source: dict[str, str], case_class: str, expected: str) -> None:
        rows.append(
            {
                "case_id": case_id,
                "corpus_partition": "historical_regression",
                "case_class": case_class,
                "execution_tier": "compact",
                "source_kind": "historical_annotation",
                "source_path": source["source_receipt_path"],
                "source_key": source["pair_digest"],
                "sequence_encoding": "historical_identity",
                "alphabet": "ACGTN",
                "query_length": "NA",
                "reference_length": "NA",
                "query_sha256": source["query_sha256"],
                "reference_sha256": source["target_sha256"],
                "pair_digest_schema": EXCLUSION_PAIR_SCHEMA,
                "pair_digest": source["pair_digest"],
                "generator": "none",
                "seed": "NA",
                "generator_parameters_json": compact_json(
                    {"query_id": source["query_id"], "target_id": source["target_id"]}
                ),
                "expected_max_score": "historical",
                "expected_property": expected,
                "contract_layers": "L0-L8",
                "holdout_eligible": 0,
            }
        )

    pair_lookup = {
        (row["query_id"], row["target_id"]): row
        for row in registry
        if row["record_type"] == "pair"
    }
    add_annotation(
        "known-hq10-ht02-traceback",
        pair_lookup[("hq10", "ht02")],
        "known_mismatch",
        "first_divergent_layer_L5_alternative_gap_placement",
    )
    add_annotation(
        "known-hq11-ht02-endpoint",
        pair_lookup[("hq11", "ht02")],
        "known_mismatch",
        "first_divergent_layer_L4_reverse_start_then_L5_L6",
    )
    add_annotation(
        "known-hq04-ht02-full-output",
        pair_lookup[("hq04", "ht02")],
        "full_output_diagnostic",
        "L7_equal_L8_diagnostic_difference",
    )
    add_annotation(
        "known-hq12-ht02-full-output",
        pair_lookup[("hq12", "ht02")],
        "full_output_diagnostic",
        "historical_v1_L8_difference_v2_L8_equal_diagnostic_only",
    )
    for index, source in enumerate(
        sorted(
            (row for row in registry if row["record_type"] == "pair" and row["query_id"] == "H19"),
            key=lambda row: row["target_id"],
        ),
        1,
    ):
        add_annotation(
            f"h19-core-{index:02d}-{source['target_id']}",
            source,
            "h19_core",
            "historical_long_query_regression",
        )
    return rows


def tiny_exhaustive_rows() -> list[dict[str, Any]]:
    strings = [
        "".join(value).encode("ascii")
        for length in (1, 2, 3)
        for value in itertools.product("AC", repeat=length)
    ]
    require(len(strings) == 14, "tiny alphabet enumeration drift")
    rows: list[dict[str, Any]] = []
    for query_index, query in enumerate(strings):
        for reference_index, reference in enumerate(strings):
            score = smith_waterman_max_score(query, reference)
            rows.append(
                generated_row(
                    case_id=f"tiny-ac-q{query_index:02d}-r{reference_index:02d}",
                    partition="tiny_exhaustive",
                    case_class="ac_lengths_1_to_3",
                    tier="compact",
                    query=query,
                    reference=reference,
                    encoding="ascii",
                    alphabet="AC",
                    generator="cartesian_product",
                    seed="NA",
                    parameters={
                        "alphabet": "AC",
                        "query": query.decode("ascii"),
                        "reference": reference.decode("ascii"),
                        "lengths": [1, 2, 3],
                    },
                    expected_max_score=score,
                    expected_property=("zero_score" if score == 0 else "exact_scalar_score"),
                    layers="L0-L6",
                )
            )
    require(len(rows) == 196, "tiny exhaustive case-count drift")
    return rows


def adversarial_rows() -> list[dict[str, Any]]:
    cases: list[tuple[str, str, bytes, bytes, str, str, str]] = [
        ("adv-homopolymer", "homopolymer", b"A" * 64, b"A" * 64, "ascii", "ACGT", "long_equal_run"),
        ("adv-periodic-repeat", "periodic_repeat", periodic(b"ACGT", 96), periodic(b"CGTA", 96), "ascii", "ACGT", "periodic_phase_shift"),
        ("adv-palindrome-rc", "palindrome_reverse_complement", b"ACGTACGT", b"TTACGTACGTAA", "ascii", "ACGT", "reverse_complement_palindrome"),
        ("adv-equal-forward", "equal_forward_endpoints", b"ACGT", b"ACGTNNNNACGT", "ascii", "ACGTN", "earliest_equal_forward_endpoint"),
        ("adv-equal-reverse", "equal_reverse_starts", b"AAAACAAA", b"AAAAGAAAACAAA", "ascii", "ACGT", "descending_reverse_scan_tie"),
        ("adv-equal-gap", "equal_gap_placements", b"ACACACAC", b"ACACAC", "ascii", "AC", "multiple_equal_gap_placements"),
        ("adv-open-extend", "open_extend_tie", b"AAAAACAAAAA", b"AAAAAAAAAA", "ascii", "AC", "affine_open_extend_tie"),
        ("adv-e-f", "e_f_tie", b"ACACAC", b"CACACA", "ascii", "AC", "E_F_equal_score_cell"),
        ("adv-diagonal-gap", "diagonal_gap_tie", b"AGAGAGA", b"GAGAGAG", "ascii", "AG", "diagonal_gap_equal_score_cell"),
        ("adv-supported-n", "supported_unknown_n", b"ACNGT", b"ACAGT", "ascii", "ACGTN", "N_maps_to_unknown"),
        ("adv-supported-u", "supported_u_translation", b"ACUGT", b"ACAGT", "ascii", "ACGTU", "U_maps_to_A"),
        ("adv-supported-lowercase", "supported_lowercase", b"acgt", b"ACGT", "ascii", "ACGTacgt", "case_insensitive_translation"),
        ("adv-empty-query", "unsupported_empty_query", b"", b"A", "raw_bytes", "raw", "fail_closed"),
        ("adv-empty-reference", "unsupported_empty_reference", b"A", b"", "raw_bytes", "raw", "fail_closed"),
        ("adv-non-ascii", "unsupported_non_ascii", b"A\x80", b"AA", "raw_bytes", "raw", "fail_closed_before_translation_table"),
        ("adv-nul", "unsupported_nul", b"A\x00", b"AA", "raw_bytes", "raw", "fail_closed_embedded_nul"),
    ]
    score_boundaries = {
        253: (
            b"TTCCCCCAGTATCTCGTCCTCGAATGTAGATCGATCTAGCCCTCCAAACTTATACGA",
            b"TTCCCCCAGTATCTCGTCCTCGAATGTATGCTCGATCGATCTAGCCCTCCAAACTTATACGA",
        ),
        254: (
            b"ACTGTCGTACCTAAACGCCTCCGTCGAGCAGAAGCTTGTTTGACAGTTCGCGAG",
            b"ACTGTCGTACCTAAACGCCTCCGTCGACGCAGAAGCTTGTTTGACAGTTCGCGAG",
        ),
        255: (
            b"CTGTATTGAGGTCGTGTCGTTCTGCGAGGCCGTCTGTAACAGCTCGTTGCA",
            b"CTGTATTGAGGTCGTGTCGTTCTGCGAGGCCGTCTGTAACAGCTCGTTGCA",
        ),
        256: (
            b"AGAAATGGGCATTCGTGCCTTTCGGCGTTCTTCACTAAGTAGAGAGTGCCATAAGC",
            b"AGAAATGGGCATTCGTGCCTTTCGGCGTGCTTCTTCACTAAGTAGAGAGTGCCATAAGC",
        ),
    }
    for score, (query, reference) in score_boundaries.items():
        require(smith_waterman_max_score(query, reference) == score, f"score-{score} construction drift")
        cases.append(
            (
                f"adv-byte-boundary-{score}",
                f"byte_boundary_{score}",
                query,
                reference,
                "ascii",
                "ACGT",
                f"final_max_score_{score}",
            )
        )

    rows: list[dict[str, Any]] = []
    for case_id, case_class, query, reference, encoding, alphabet, property_name in cases:
        unsupported = case_class.startswith("unsupported_")
        score: str | int = "FAIL_CLOSED" if unsupported else smith_waterman_max_score(query, reference)
        rows.append(
            generated_row(
                case_id=case_id,
                partition="adversarial",
                case_class=case_class,
                tier="compact",
                query=query,
                reference=reference,
                encoding=encoding,
                alphabet=alphabet,
                generator="explicit",
                seed="NA",
                parameters={"query_hex": query.hex(), "reference_hex": reference.hex()},
                expected_max_score=score,
                expected_property=property_name,
                layers="L0-L6",
            )
        )

    for length in LENGTH_BOUNDARIES:
        query = periodic(b"ACGT", length)
        reference = bytearray(query)
        reference[length // 2] = ord("T") if reference[length // 2] != ord("T") else ord("A")
        tier = "compact" if length <= 257 else "large"
        expected_score: str | int = (
            smith_waterman_max_score(query, bytes(reference)) if tier == "compact" else "DEFERRED_AUTHORITY"
        )
        rows.append(
            generated_row(
                case_id=f"adv-length-{length:04d}",
                partition="adversarial",
                case_class="length_boundary",
                tier=tier,
                query=query,
                reference=bytes(reference),
                encoding="ascii",
                alphabet="ACGT",
                generator="periodic_single_substitution",
                seed="NA",
                parameters={"length": length, "pattern": "ACGT", "mutation_index": length // 2},
                expected_max_score=expected_score,
                expected_property=f"query_and_reference_length_{length}",
                layers="L0-L6",
            )
        )
    classes = {row["case_class"] for row in rows}
    require(REQUIRED_ADVERSARIAL_CLASSES <= classes, "adversarial class coverage drift")
    return rows


def fuzz_rows(seed: int, count: int, tier: str) -> list[dict[str, Any]]:
    require(tier in {"compact", "large"}, "invalid fuzz tier")
    rng = SplitMix64(seed)
    profiles = ("uniform", "gc_low", "gc_high", "repeat")
    rows: list[dict[str, Any]] = []
    for index in range(count):
        profile = profiles[index % len(profiles)]
        if tier == "compact":
            query_length = 1 + rng.randbelow(96)
            reference_length = 1 + rng.randbelow(128)
            length_rule = "query_1_96_reference_1_128"
        else:
            if index < len(LENGTH_BOUNDARIES):
                query_length = LENGTH_BOUNDARIES[index]
                reference_length = LENGTH_BOUNDARIES[-index - 1]
            else:
                query_length = 64 + rng.randbelow(2812 - 64 + 1)
                reference_length = 64 + rng.randbelow(2812 - 64 + 1)
            length_rule = "boundaries_then_uniform_64_2812"
        query = fuzz_sequence(rng, query_length, profile)
        reference = fuzz_sequence(rng, reference_length, profiles[(index + 1) % len(profiles)])
        rows.append(
            generated_row(
                case_id=f"fuzz-{tier}-{index:04d}",
                partition="deterministic_fuzz",
                case_class=f"{tier}_{profile}",
                tier=tier,
                query=query,
                reference=reference,
                encoding="ascii",
                alphabet="ACGT",
                generator="splitmix64",
                seed=f"0x{seed:016x}",
                parameters={
                    "index": index,
                    "profile": profile,
                    "reference_profile": profiles[(index + 1) % len(profiles)],
                    "length_rule": length_rule,
                },
                expected_max_score="DEFERRED_AUTHORITY",
                expected_property="deterministic_fuzz_regression",
                layers="L0-L6",
            )
        )
    return rows


def build_manifest_rows() -> list[dict[str, Any]]:
    registry = load_registry()
    rows = (
        historical_rows(registry)
        + tiny_exhaustive_rows()
        + adversarial_rows()
        + fuzz_rows(COMPACT_FUZZ_SEED, COMPACT_FUZZ_COUNT, "compact")
        + fuzz_rows(LARGE_FUZZ_SEED, LARGE_FUZZ_COUNT, "large")
    )
    require(len(rows) == len({row["case_id"] for row in rows}), "duplicate corpus case_id")
    require(all(row["holdout_eligible"] == 0 for row in rows), "corpus row marked holdout eligible")
    registry_digests = {
        row[field]
        for row in registry
        for field in ("query_sha256", "target_sha256")
        if row[field] != "NA"
    }
    generated_digests = {
        row[field]
        for row in rows
        if row["source_kind"] == "generated"
        for field in ("query_sha256", "reference_sha256")
    }
    require(not (registry_digests & generated_digests), "generated corpus overlaps historical sequence digest")
    return rows


def registry_coverage(rows: list[dict[str, Any]], registry: list[dict[str, str]]) -> dict[str, Any]:
    identity_rows = [row for row in rows if row["source_kind"] == "used_input_exclusion_registry"]
    require(len(identity_rows) == len(registry), "not every registry row is represented")
    represented = {
        (row["query_sha256"], row["reference_sha256"], row["pair_digest"])
        for row in identity_rows
    }
    expected = {
        (row["query_sha256"], row["target_sha256"], row["pair_digest"])
        for row in registry
    }
    require(represented == expected, "registry identity coverage drift")
    reasons = Counter(
        reason
        for row in registry
        for reason in row["exclusion_reason"].split(";")
    )
    require(REQUIRED_EXCLUSION_REASONS <= set(reasons), "required exclusion class missing")
    sources = sorted(
        {
            source
            for row in registry
            for source in row["source_receipt_path"].split(";")
        }
    )
    return {
        "registry_rows": len(registry),
        "manifest_identity_rows": len(identity_rows),
        "all_registry_rows_represented": True,
        "required_exclusion_reasons": sorted(REQUIRED_EXCLUSION_REASONS),
        "reason_row_counts": dict(sorted(reasons.items())),
        "source_receipt_paths": sources,
    }


def build_receipt(
    rows: list[dict[str, Any]],
    manifest_payload: bytes,
    *,
    frozen_parent_head: str,
    frozen_utc: str,
) -> dict[str, Any]:
    registry = load_registry()
    counts_by_partition = Counter(row["corpus_partition"] for row in rows)
    counts_by_tier = Counter(row["execution_tier"] for row in rows)
    counts_by_class = Counter(row["case_class"] for row in rows)
    tiny_rows = [row for row in rows if row["corpus_partition"] == "tiny_exhaustive"]
    require(any(row["expected_max_score"] == 0 for row in tiny_rows), "tiny corpus lacks zero score")
    return {
        "schema_version": 1,
        "status": "pass",
        "phase": 3,
        "frozen_parent_head": frozen_parent_head,
        "frozen_utc": frozen_utc,
        "generator": {
            "version": GENERATOR_VERSION,
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "compact_fuzz_seed": f"0x{COMPACT_FUZZ_SEED:016x}",
            "compact_fuzz_count": COMPACT_FUZZ_COUNT,
            "large_fuzz_seed": f"0x{LARGE_FUZZ_SEED:016x}",
            "large_fuzz_count": LARGE_FUZZ_COUNT,
            "prng": "SplitMix64_v1",
        },
        "manifest": {
            "path": str(MANIFEST.relative_to(ROOT)),
            "sha256": sha256_bytes(manifest_payload),
            "row_count": len(rows),
            "counts_by_partition": dict(sorted(counts_by_partition.items())),
            "counts_by_execution_tier": dict(sorted(counts_by_tier.items())),
            "counts_by_case_class": dict(sorted(counts_by_class.items())),
        },
        "tiny_exhaustive": {
            "alphabet": "AC",
            "query_lengths": [1, 2, 3],
            "reference_lengths": [1, 2, 3],
            "string_count_per_role": 14,
            "cartesian_case_count": 196,
            "contains_zero_score": True,
            "contains_single_match": True,
            "truncation_rule": "none",
        },
        "adversarial": {
            "required_classes": sorted(REQUIRED_ADVERSARIAL_CLASSES),
            "length_boundaries": list(LENGTH_BOUNDARIES),
            "byte_score_boundaries": [253, 254, 255, 256],
            "all_required_classes_present": REQUIRED_ADVERSARIAL_CLASSES <= set(counts_by_class),
        },
        "registry_coverage": registry_coverage(rows, registry),
        "bindings": {
            "used_input_exclusion_registry_path": str(REGISTRY.relative_to(ROOT)),
            "used_input_exclusion_registry_sha256": sha256_file(REGISTRY),
            "holdout_policy_path": str(POLICY.relative_to(ROOT)),
            "holdout_policy_sha256": sha256_file(POLICY),
            "layered_comparator_path": str(COMPARATOR.relative_to(ROOT)),
            "layered_comparator_sha256": sha256_file(COMPARATOR),
        },
        "known_mismatch_classification": {
            "hq10_ht02": "first_divergent_layer_L5",
            "hq11_ht02": "first_divergent_layer_L4",
            "root_cause": (
                "reproducible GASAL2 GPU endpoint/CIGAR traceback divergence, "
                "consistent with an alternative reported-equal-score alignment path"
            ),
            "specific_dp_tie_cell_proven": False,
        },
        "execution_policy": {
            "identity_only_rows_are_not_automatically_executed": True,
            "compact_rows_are_normal_regression": True,
            "large_rows_require_explicit_expensive_gate": True,
            "normal_checker_runs_large_corpus": False,
            "fresh_holdout_consumed": False,
            "l8_contract_status": "diagnostic_only",
        },
    }


def build_outputs(frozen_parent_head: str, frozen_utc: str) -> dict[Path, bytes]:
    require(re.fullmatch(r"[0-9a-f]{40}", frozen_parent_head) is not None, "invalid frozen parent HEAD")
    require(frozen_utc.endswith("Z") or "+00:00" in frozen_utc, "frozen UTC must include UTC offset")
    rebuild_registry()
    rows = build_manifest_rows()
    manifest_payload = tsv_bytes(MANIFEST_FIELDS, rows)
    manifest_sha = sha256_bytes(manifest_payload)
    receipt = build_receipt(
        rows,
        manifest_payload,
        frozen_parent_head=frozen_parent_head,
        frozen_utc=frozen_utc,
    )
    return {
        MANIFEST: manifest_payload,
        MANIFEST_CHECKSUM: f"{manifest_sha}  {MANIFEST.name}\n".encode("ascii"),
        RECEIPT: json_bytes(receipt),
    }


def write_outputs(outputs: dict[Path, bytes]) -> None:
    for path, payload in outputs.items():
        require(not path.is_symlink(), f"unsafe output path: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def check_outputs() -> None:
    for path in (MANIFEST, MANIFEST_CHECKSUM, RECEIPT):
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 3 output: {path}")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    require(receipt.get("schema_version") == 1 and receipt.get("status") == "pass", "receipt status drift")
    outputs = build_outputs(receipt["frozen_parent_head"], receipt["frozen_utc"])
    for path, expected in outputs.items():
        require(path.read_bytes() == expected, f"Phase 3 generated output drift: {path}")
    require(receipt["execution_policy"]["l8_contract_status"] == "diagnostic_only", "L8 boundary drift")
    require(not receipt["execution_policy"]["normal_checker_runs_large_corpus"], "large corpus auto-run drift")
    require(not receipt["execution_policy"]["fresh_holdout_consumed"], "Phase 3 consumed fresh holdout")


def validate_holdout_candidates(candidates: Any, registry_rows: list[dict[str, str]] | None = None) -> dict[str, Any]:
    require(isinstance(candidates, list) and candidates, "holdout candidate file must be a nonempty array")
    registry = registry_rows if registry_rows is not None else load_registry()
    query_ordinals = {
        (row["query_ordinal_namespace"], row["query_source_ordinal"])
        for row in registry
        if row["query_source_ordinal"] != "NA"
    }
    target_ordinals = {
        (row["target_ordinal_namespace"], row["target_source_ordinal"])
        for row in registry
        if row["target_source_ordinal"] != "NA"
    }
    query_digests = {row["query_sha256"] for row in registry if row["query_sha256"] != "NA"}
    target_digests = {row["target_sha256"] for row in registry if row["target_sha256"] != "NA"}
    pair_digests = {row["pair_digest"] for row in registry if row["pair_digest"] != "NA"}
    receipt_paths = {
        source
        for row in registry
        for source in row["source_receipt_path"].split(";")
    }
    required_fields = {
        "candidate_id",
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
        "source_receipt_path",
        "usage_tags",
    }
    all_overlaps: list[dict[str, Any]] = []
    seen_candidate_ids: set[str] = set()
    for index, raw in enumerate(candidates):
        require(isinstance(raw, dict), f"candidate {index} must be an object")
        missing = required_fields - set(raw)
        require(not missing, f"candidate {index} missing fields: {sorted(missing)}")
        candidate_id = raw["candidate_id"]
        require(isinstance(candidate_id, str) and candidate_id, f"candidate {index} ID missing")
        require(candidate_id not in seen_candidate_ids, f"duplicate candidate_id: {candidate_id}")
        seen_candidate_ids.add(candidate_id)
        for digest_field in ("query_sha256", "target_sha256", "pair_digest"):
            require(
                isinstance(raw[digest_field], str) and SHA256_RE.fullmatch(raw[digest_field]) is not None,
                f"{candidate_id} invalid {digest_field}",
            )
        for field in (
            "query_ordinal_namespace",
            "query_source_ordinal",
            "target_ordinal_namespace",
            "target_source_ordinal",
            "query_id",
            "target_id",
            "query_region",
            "target_region",
            "source_receipt_path",
        ):
            require(isinstance(raw[field], str) and raw[field] and raw[field] != "NA", f"{candidate_id} invalid {field}")
        require(isinstance(raw["usage_tags"], list), f"{candidate_id} usage_tags must be an array")
        identity = {
            "query_ordinal_namespace": raw["query_ordinal_namespace"],
            "query_source_ordinal": raw["query_source_ordinal"],
            "target_ordinal_namespace": raw["target_ordinal_namespace"],
            "target_source_ordinal": raw["target_source_ordinal"],
            "query_id": raw["query_id"],
            "target_id": raw["target_id"],
            "query_sha256": raw["query_sha256"],
            "target_sha256": raw["target_sha256"],
            "query_region": raw["query_region"],
            "target_region": raw["target_region"],
        }
        require(
            raw["pair_digest"] == exclusion_pair_digest(identity),
            f"{candidate_id} pair_digest does not bind its identity",
        )
        reasons: list[str] = []
        if (raw["query_ordinal_namespace"], raw["query_source_ordinal"]) in query_ordinals:
            reasons.append("query_source_ordinal_overlap")
        if (raw["target_ordinal_namespace"], raw["target_source_ordinal"]) in target_ordinals:
            reasons.append("target_source_ordinal_overlap")
        if raw["query_sha256"] in query_digests:
            reasons.append("query_sequence_digest_overlap")
        if raw["target_sha256"] in target_digests:
            reasons.append("target_sequence_digest_overlap")
        if raw["pair_digest"] in pair_digests:
            reasons.append("pair_digest_overlap")
        if raw["source_receipt_path"] in receipt_paths:
            reasons.append("prior_receipt_reference_overlap")
        prior_tags = sorted(set(raw["usage_tags"]) & DISALLOWED_PRIOR_USE_TAGS)
        if prior_tags:
            reasons.append("prior_use:" + ",".join(prior_tags))
        if reasons:
            all_overlaps.append({"candidate_id": candidate_id, "reasons": reasons})
    if all_overlaps:
        raise HoldoutOverlapError("holdout overlap: " + compact_json(all_overlaps))
    return {
        "schema_version": 1,
        "status": "pass",
        "candidate_count": len(candidates),
        "registry_row_count": len(registry),
        "overlap_count": 0,
        "names_used_for_selection": False,
        "result_based_replacement_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-holdout", type=Path)
    parser.add_argument("--frozen-parent-head")
    parser.add_argument("--frozen-utc")
    arguments = parser.parse_args()
    if arguments.write:
        require(arguments.frozen_parent_head is not None, "--write requires --frozen-parent-head")
        require(arguments.frozen_utc is not None, "--write requires --frozen-utc")
        write_outputs(build_outputs(arguments.frozen_parent_head, arguments.frozen_utc))
    elif arguments.check:
        check_outputs()
    else:
        path = arguments.check_holdout
        assert path is not None
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe holdout candidates: {path}")
        candidates = json.loads(path.read_text(encoding="utf-8"))
        print(json.dumps(validate_holdout_candidates(candidates), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CorpusError as error:
        print(f"Phase 3 corpus error: {error}", file=sys.stderr)
        raise SystemExit(1)
