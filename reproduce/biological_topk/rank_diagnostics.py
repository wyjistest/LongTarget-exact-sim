#!/usr/bin/env python3
"""Exact rank-displacement and finite RBO diagnostics."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Sequence

try:
    from . import contract
except ImportError:  # pragma: no cover
    import contract  # type: ignore[no-redef]


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def fraction_decimal(value: Fraction, *, precision: int = 30) -> str:
    with localcontext() as context:
        context.prec = precision
        rendered = Decimal(value.numerator) / Decimal(value.denominator)
    return contract.canonical_decimal(rendered)


def rank_diagnostics(
    authority_count: int,
    candidate_count: int,
    pairs: Sequence[tuple[int, int]],
    *,
    depth: int = 5,
    persistence: Fraction = Fraction(9, 10),
) -> dict[str, Any]:
    if authority_count < 0 or candidate_count < 0:
        raise contract.ContractError("candidate counts must be nonnegative")
    authority_tokens = [f"matched:{index}" for index in range(authority_count)]
    candidate_tokens = [f"candidate-unmatched:{index}" for index in range(candidate_count)]
    seen_left: set[int] = set()
    seen_right: set[int] = set()
    displacements: list[dict[str, int]] = []
    for left_index, right_index in pairs:
        if (
            not 0 <= left_index < authority_count
            or not 0 <= right_index < candidate_count
            or left_index in seen_left
            or right_index in seen_right
        ):
            raise contract.ContractError("rank diagnostics received an invalid one-to-one pair set")
        seen_left.add(left_index)
        seen_right.add(right_index)
        candidate_tokens[right_index] = authority_tokens[left_index]
        displacements.append(
            {
                "authority_rank": left_index + 1,
                "candidate_rank": right_index + 1,
                "candidate_minus_authority": right_index - left_index,
                "absolute_displacement": abs(right_index - left_index),
            }
        )
    value = contract.finite_rbo(
        authority_tokens,
        candidate_tokens,
        depth=depth,
        persistence=persistence,
    )
    return {
        "depth": depth,
        "persistence": fraction_text(persistence),
        "finite_rbo_fraction": fraction_text(value),
        "finite_rbo_decimal": fraction_decimal(value),
        "rank_displacements": sorted(
            displacements,
            key=lambda row: (row["authority_rank"], row["candidate_rank"]),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute exact finite-depth rank diagnostics.")
    parser.add_argument("--authority-count", required=True, type=int)
    parser.add_argument("--candidate-count", required=True, type=int)
    parser.add_argument(
        "--pairs-json",
        required=True,
        help='JSON array of zero-based pairs, for example "[[0,0],[1,2]]"',
    )
    parser.add_argument("--depth", type=int, default=5)
    args = parser.parse_args()
    try:
        raw_pairs = json.loads(args.pairs_json)
        pairs = tuple((int(pair[0]), int(pair[1])) for pair in raw_pairs)
        result = rank_diagnostics(
            args.authority_count,
            args.candidate_count,
            pairs,
            depth=args.depth,
        )
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, contract.ContractError) as error:
        parser.exit(2, f"rank diagnostics failed: {error}\n")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("_")]
