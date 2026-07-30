#!/usr/bin/env python3
"""One-sided exact binomial bounds used by biological Top-K gates."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, localcontext
from typing import Any, Iterable, Mapping

try:
    from . import contract
except ImportError:  # pragma: no cover
    import contract  # type: ignore[no-redef]


def _ratio(successes: int, trials: int) -> str | None:
    if trials == 0:
        return None
    with localcontext() as context:
        context.prec = 50
        value = Decimal(successes) / Decimal(trials)
    return contract.canonical_decimal(value)


def exact_binomial_bound(
    successes: int,
    trials: int,
    *,
    alpha: Decimal | str = "0.05",
    threshold: Decimal | str = "0.95",
) -> dict[str, Any]:
    if trials < 0 or successes < 0 or successes > trials:
        raise contract.ContractError("exact binomial counts require 0 <= successes <= trials")
    alpha_decimal = contract.parse_decimal(alpha) if isinstance(alpha, str) else alpha
    threshold_decimal = (
        contract.parse_decimal(threshold) if isinstance(threshold, str) else threshold
    )
    if not 0 < alpha_decimal < 1 or not 0 <= threshold_decimal <= 1:
        raise contract.ContractError("invalid exact binomial alpha or threshold")
    lower = None if trials == 0 else contract.clopper_pearson_lower(successes, trials, alpha_decimal)
    return {
        "successes": successes,
        "trials": trials,
        "estimate": _ratio(successes, trials),
        "alpha_one_sided": contract.canonical_decimal(alpha_decimal),
        "lower_confidence_bound": (
            None if lower is None else contract.canonical_decimal(lower)
        ),
        "promotion_threshold": contract.canonical_decimal(threshold_decimal),
        "threshold_pass": bool(lower is not None and lower >= threshold_decimal),
        "method": "one_sided_exact_clopper_pearson",
    }


def endpoint_bounds(
    rows: Iterable[Mapping[str, Any]],
    *,
    endpoint_field: str,
    denominator_field: str = "binary_gate_denominator_eligible",
    alpha: Decimal | str = "0.05",
    threshold: Decimal | str = "0.95",
) -> dict[str, Any]:
    eligible = [row for row in rows if row.get(denominator_field) in {True, 1, "1"}]
    successes = sum(row.get(endpoint_field) in {True, 1, "1"} for row in eligible)
    result = exact_binomial_bound(
        successes,
        len(eligible),
        alpha=alpha,
        threshold=threshold,
    )
    result["endpoint_field"] = endpoint_field
    result["denominator_field"] = denominator_field
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute a one-sided exact binomial LCB.")
    parser.add_argument("--successes", required=True, type=int)
    parser.add_argument("--trials", required=True, type=int)
    parser.add_argument("--alpha", default="0.05")
    parser.add_argument("--threshold", default="0.95")
    args = parser.parse_args()
    try:
        result = exact_binomial_bound(
            args.successes,
            args.trials,
            alpha=args.alpha,
            threshold=args.threshold,
        )
    except contract.ContractError as error:
        parser.exit(2, f"exact binomial bound failed: {error}\n")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("_")]
