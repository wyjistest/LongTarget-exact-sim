#!/usr/bin/env python3
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

BLOCKED_RUNTIME_PROTOTYPES = [
    "lazy_generation_index",
    "incoming_key_coalescing",
    "victim_slot_event_reorder",
    "full_set_miss_batch_collapse",
]

CASE_FIELDNAMES = [
    "audit_dir",
    "case_id",
    "decision_status",
    "locality_status",
    "exactness_hazard_status",
    "recommended_runtime_prototype",
    "observed_full_set_miss_count",
    "incoming_key_reuse_before_eviction_share",
    "victim_key_reappears_after_eviction_share",
    "floor_change_per_full_set_miss",
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--min-case-count", type=int, default=5)
    parser.add_argument("--victim-strong-key-weak-threshold", type=float, default=0.70)
    parser.add_argument("--low-hazard-threshold", type=float, default=0.80)
    parser.add_argument("--hazard-dominant-threshold", type=float, default=0.20)
    parser.add_argument("--mixed-hazard-case-limit", type=int, default=1)
    parser.add_argument("--mixed-hazard-action-threshold", type=float, default=0.95)
    parser.add_argument("--mixed-blocker-metric-threshold", type=float, default=0.50)
    args = parser.parse_args()
    if args.min_case_count <= 0:
        raise SystemExit("--min-case-count must be > 0")
    return args


def share(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_cases(audit_dir: Path):
    summary_path = audit_dir / "summary.json"
    decision_path = audit_dir / "decision.json"
    hazard_path = audit_dir / "hazard_summary.json"
    missing = [str(path.name) for path in [summary_path, decision_path, hazard_path] if not path.exists()]
    if missing:
        raise ValueError(f"{audit_dir}: missing required files: {', '.join(missing)}")

    summary = load_json(summary_path)
    decision = load_json(decision_path)
    hazard = load_json(hazard_path)

    decision_status = decision.get("decision_status", "unknown")
    if summary.get("decision_status") != decision_status:
        raise ValueError(f"{audit_dir}: summary/decision status mismatch")

    cases = hazard.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"{audit_dir}: hazard_summary.json missing cases list")

    rows = []
    summary_metrics = summary.get("aggregate_metrics", {})
    for case in cases:
        case_id = case.get("case_id")
        if not case_id:
            raise ValueError(f"{audit_dir}: case missing case_id")
        miss_count = int(case.get("observed_full_set_miss_count", 0))
        metrics = case.get("metrics", {})
        rows.append(
            {
                "audit_dir": str(audit_dir),
                "case_id": case_id,
                "decision_status": decision_status,
                "locality_status": case.get("locality_status", summary.get("locality_status", "unknown")),
                "exactness_hazard_status": case.get(
                    "exactness_hazard_status",
                    summary.get("exactness_hazard_status", "unknown"),
                ),
                "recommended_runtime_prototype": case.get(
                    "recommended_runtime_prototype",
                    summary.get("recommended_runtime_prototype", "none"),
                ),
                "observed_full_set_miss_count": miss_count,
                "incoming_key_reuse_before_eviction_share": float(
                    metrics.get(
                        "incoming_key_reuse_before_eviction_share",
                        summary_metrics.get("incoming_key_reuse_before_eviction_share", 0.0),
                    )
                ),
                "victim_key_reappears_after_eviction_share": float(
                    metrics.get(
                        "victim_key_reappears_after_eviction_share",
                        summary_metrics.get("victim_key_reappears_after_eviction_share", 0.0),
                    )
                ),
                "floor_change_per_full_set_miss": float(
                    metrics.get(
                        "floor_change_per_full_set_miss",
                        summary_metrics.get("floor_change_per_full_set_miss", 0.0),
                    )
                ),
            }
        )
    return summary, decision, rows


def compute_case_weighted(case_rows):
    return {
        "locality_status_counts": dict(Counter(row["locality_status"] for row in case_rows)),
        "exactness_hazard_status_counts": dict(
            Counter(row["exactness_hazard_status"] for row in case_rows)
        ),
        "recommended_runtime_prototype_counts": dict(
            Counter(row["recommended_runtime_prototype"] for row in case_rows)
        ),
    }


def compute_event_weighted(case_rows):
    total = sum(int(row["observed_full_set_miss_count"]) for row in case_rows)

    def event_sum(predicate):
        return sum(
            int(row["observed_full_set_miss_count"])
            for row in case_rows
            if predicate(row)
        )

    victim_strong_events = event_sum(
        lambda row: row["locality_status"]
        in {"victim_strong_key_weak", "victim_strong_key_mixed"}
    )
    victim_strong_key_weak_events = event_sum(
        lambda row: row["locality_status"] == "victim_strong_key_weak"
    )
    key_reuse_events = event_sum(lambda row: row["exactness_hazard_status"] == "key_reuse")
    floor_churn_events = event_sum(lambda row: row["exactness_hazard_status"] == "floor_churn")
    mixed_hazard_events = event_sum(lambda row: row["exactness_hazard_status"] == "mixed")
    low_hazard_events = event_sum(lambda row: row["exactness_hazard_status"] == "low")
    victim_reappearance_dominant_events = event_sum(
        lambda row: row["victim_key_reappears_after_eviction_share"] >= 0.50
    )
    floor_change_dominant_events = event_sum(
        lambda row: row["floor_change_per_full_set_miss"] >= 0.50
    )

    return {
        "full_set_miss_count": total,
        "victim_strong_event_share": share(victim_strong_events, total),
        "victim_strong_key_weak_event_share": share(victim_strong_key_weak_events, total),
        "key_reuse_hazard_event_share": share(key_reuse_events, total),
        "floor_churn_hazard_event_share": share(floor_churn_events, total),
        "mixed_hazard_event_share": share(mixed_hazard_events, total),
        "low_hazard_event_share": share(low_hazard_events, total),
        "victim_key_reappears_dominant_event_share": share(
            victim_reappearance_dominant_events,
            total,
        ),
        "floor_change_dominant_event_share": share(
            floor_change_dominant_events,
            total,
        ),
    }


def make_not_ready(case_rows, errors):
    return {
        "decision_status": "not_ready",
        "case_count": len(case_rows),
        "ready_case_count": sum(1 for row in case_rows if row["decision_status"] == "ready"),
        "schema_version_all": None,
        "case_weighted": compute_case_weighted(case_rows) if case_rows else {},
        "event_weighted": compute_event_weighted(case_rows) if case_rows else {},
        "blocking_reasons": errors,
        "dominant_blockers": [],
        "recommended_runtime_prototype": "none",
        "next_action": "fix_audit_inputs",
    }


def dominant_blockers_from_event_weighted(event_weighted, args):
    blockers = []
    if (
        event_weighted["victim_key_reappears_dominant_event_share"]
        >= args.mixed_hazard_action_threshold
    ):
        blockers.append("victim_key_reappears_after_eviction")
    if (
        event_weighted["floor_change_dominant_event_share"]
        >= args.mixed_hazard_action_threshold
    ):
        blockers.append("floor_churn")
    return blockers

def decide_ready(case_rows, args):
    case_weighted = compute_case_weighted(case_rows)
    event_weighted = compute_event_weighted(case_rows)
    mixed_case_count = case_weighted["exactness_hazard_status_counts"].get("mixed", 0)
    blocking_reasons = []
    dominant_blockers = dominant_blockers_from_event_weighted(event_weighted, args)

    if len(case_rows) < args.min_case_count:
        blocking_reasons.append(
            f"need at least {args.min_case_count} cases, got {len(case_rows)}"
        )
    if event_weighted["victim_strong_key_weak_event_share"] < args.victim_strong_key_weak_threshold:
        blocking_reasons.append(
            "victim_strong_key_weak_event_share below threshold"
        )
    if event_weighted["low_hazard_event_share"] < args.low_hazard_threshold:
        blocking_reasons.append("low_hazard_event_share below threshold")
    if event_weighted["key_reuse_hazard_event_share"] > args.hazard_dominant_threshold:
        blocking_reasons.append("key_reuse hazard dominates heavy campaign")
    if event_weighted["floor_churn_hazard_event_share"] > args.hazard_dominant_threshold:
        blocking_reasons.append("floor_churn hazard dominates heavy campaign")
    if event_weighted["mixed_hazard_event_share"] > args.hazard_dominant_threshold:
        blocking_reasons.append("mixed hazard event share too high")
    if mixed_case_count > args.mixed_hazard_case_limit:
        blocking_reasons.append("too many mixed hazard cases")

    if not blocking_reasons:
        recommended_runtime_prototype = "lazy_generation_index"
        next_action = "prototype_lazy_generation_index"
    else:
        recommended_runtime_prototype = "none"
        if (
            len(case_rows) >= args.min_case_count
            and event_weighted["mixed_hazard_event_share"] >= args.mixed_hazard_action_threshold
            and event_weighted["victim_strong_event_share"] >= args.mixed_hazard_action_threshold
            and event_weighted["low_hazard_event_share"] <= 0.0
            and dominant_blockers == [
                "victim_key_reappears_after_eviction",
                "floor_churn",
            ]
        ):
            next_action = "split_mixed_floor_reappearance_hazard"
        elif event_weighted["key_reuse_hazard_event_share"] > args.hazard_dominant_threshold:
            next_action = "inspect_key_reuse"
        elif event_weighted["floor_churn_hazard_event_share"] > args.hazard_dominant_threshold:
            next_action = "inspect_floor_churn"
        else:
            next_action = "expand_campaign"

    return {
        "decision_status": "ready",
        "case_count": len(case_rows),
        "ready_case_count": len(case_rows),
        "schema_version_all": 2,
        "case_weighted": case_weighted,
        "event_weighted": event_weighted,
        "blocking_reasons": blocking_reasons,
        "dominant_blockers": dominant_blockers,
        "recommended_runtime_prototype": recommended_runtime_prototype,
        "next_action": next_action,
    }


def write_summary_markdown(path: Path, decision, case_rows):
    lines = [
        "# SIM Initial Host Merge Hazard Campaign",
        "",
        f"- decision_status: `{decision['decision_status']}`",
        f"- recommended_runtime_prototype: `{decision['recommended_runtime_prototype']}`",
        f"- next_action: `{decision['next_action']}`",
        f"- case_count: `{decision['case_count']}`",
        f"- ready_case_count: `{decision['ready_case_count']}`",
        "",
    ]

    if decision.get("dominant_blockers"):
        lines.extend(["## Dominant Blockers", ""])
        for blocker in decision["dominant_blockers"]:
            lines.append(f"- {blocker}")
        lines.append("")

    if decision.get("blocking_reasons"):
        lines.extend(["## Blocking Reasons", ""])
        for reason in decision["blocking_reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

    if decision.get("event_weighted"):
        lines.extend(["## Event-Weighted", "", "| Metric | Value |", "| --- | ---: |"])
        for key, value in sorted(decision["event_weighted"].items()):
            if isinstance(value, float):
                lines.append(f"| {key} | {value:.6f} |")
            else:
                lines.append(f"| {key} | {value} |")
        lines.append("")

    if case_rows:
        lines.extend(
            [
                "## Cases",
                "",
                "| case_id | miss_count | locality | hazard | runtime | audit_dir |",
                "| --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for row in sorted(case_rows, key=lambda item: (-int(item["observed_full_set_miss_count"]), item["case_id"])):
            lines.append(
                "| {case_id} | {miss_count} | {locality} | {hazard} | {runtime} | {audit_dir} |".format(
                    case_id=row["case_id"],
                    miss_count=row["observed_full_set_miss_count"],
                    locality=row["locality_status"],
                    hazard=row["exactness_hazard_status"],
                    runtime=row["recommended_runtime_prototype"],
                    audit_dir=row["audit_dir"],
                )
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    case_rows = []
    errors = []
    seen_case_ids = set()

    for audit_dir_text in args.audit_dir:
        audit_dir = Path(audit_dir_text)
        try:
            summary, decision, rows = flatten_cases(audit_dir)
        except Exception as exc:
            errors.append(str(exc))
            continue

        if decision.get("decision_status") != "ready":
            errors.append(f"{audit_dir}: decision_status={decision.get('decision_status')}")
        for row in rows:
            if row["case_id"] in seen_case_ids:
                errors.append(f"duplicate case_id across campaign inputs: {row['case_id']}")
                continue
            seen_case_ids.add(row["case_id"])
            case_rows.append(row)

    if errors:
        campaign_decision = make_not_ready(case_rows, errors)
    else:
        campaign_decision = decide_ready(case_rows, args)

    campaign_cases_path = output_dir / "campaign_cases.tsv"
    campaign_hazard_summary_path = output_dir / "campaign_hazard_summary.json"
    campaign_decision_path = output_dir / "campaign_decision.json"
    campaign_summary_md_path = output_dir / "campaign_summary.md"

    write_rows(campaign_cases_path, CASE_FIELDNAMES, case_rows)

    aggregate = {}
    if campaign_decision["decision_status"] == "ready":
        aggregate = {
            "recommended_runtime_prototype": campaign_decision["recommended_runtime_prototype"],
            "next_action": campaign_decision["next_action"],
            **campaign_decision["event_weighted"],
        }

    campaign_hazard_summary = {
        "aggregate": aggregate,
        "case_weighted": campaign_decision.get("case_weighted", {}),
        "cases": case_rows,
        "errors": campaign_decision.get("blocking_reasons", []),
    }

    campaign_decision_json = {
        **campaign_decision,
        "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
        "campaign_cases_tsv": str(campaign_cases_path),
        "campaign_hazard_summary_json": str(campaign_hazard_summary_path),
        "campaign_summary_markdown": str(campaign_summary_md_path),
    }

    campaign_hazard_summary_path.write_text(
        json.dumps(campaign_hazard_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    campaign_decision_path.write_text(
        json.dumps(campaign_decision_json, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_summary_markdown(campaign_summary_md_path, campaign_decision_json, case_rows)


if __name__ == "__main__":
    main()
