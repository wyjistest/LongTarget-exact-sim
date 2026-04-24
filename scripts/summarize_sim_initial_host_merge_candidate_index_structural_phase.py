#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


class StructuralPhaseInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-rollup-decision", required=True)
    parser.add_argument("--candidate-index-operation-rollup-decision")
    parser.add_argument("--candidate-index-common-memory-behavior-decision")
    parser.add_argument("--candidate-index-hardware-observation-decision")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def read_json(path_text):
    path = Path(path_text)
    if not path.is_file():
        raise StructuralPhaseInputError(f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8")), path


def optional_str(mapping, key, default="unknown"):
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def build_summary(
    branch_rollup_decision,
    branch_rollup_path,
    operation_rollup_decision,
    operation_rollup_path,
    common_memory_decision,
    common_memory_path,
    hardware_observation_decision,
    hardware_observation_path,
):
    leaf_status = optional_str(
        branch_rollup_decision, "leaf_level_candidate_index_profiling_status", "unknown"
    )
    if leaf_status != "stopped":
        raise StructuralPhaseInputError(
            "candidate-index structural phase requires leaf_level_candidate_index_profiling_status=stopped"
        )

    current_focus = "operation_rollup"
    phase_status = "active"
    recommended_next_action = "profile_candidate_index_operation_rollup"
    optional_next_action = None
    stop_reason = None

    if common_memory_decision:
        optional_value = common_memory_decision.get("optional_next_action")
        optional_next_action = (
            str(optional_value).strip()
            if optional_value is not None and str(optional_value).strip() != ""
            else None
        )
        common_memory_action = optional_str(
            common_memory_decision, "recommended_next_action", "unknown"
        )
        if common_memory_action == "stop_candidate_index_structural_profiling":
            phase_status = "stopped"
            current_focus = None
            recommended_next_action = common_memory_action
            stop_reason = "no_stable_structural_signal"
        else:
            current_focus = "common_memory_behavior"
            recommended_next_action = common_memory_action
    elif operation_rollup_decision:
        optional_value = operation_rollup_decision.get("optional_next_action")
        optional_next_action = (
            str(optional_value).strip()
            if optional_value is not None and str(optional_value).strip() != ""
            else None
        )
        operation_action = optional_str(
            operation_rollup_decision, "recommended_next_action", "unknown"
        )
        if operation_action == "profile_candidate_index_common_memory_behavior":
            current_focus = "common_memory_behavior"
            recommended_next_action = operation_action
        elif operation_action == "stop_candidate_index_structural_profiling":
            phase_status = "stopped"
            current_focus = None
            recommended_next_action = operation_action
            stop_reason = "no_stable_structural_signal"
        else:
            current_focus = "operation_rollup"
            recommended_next_action = operation_action

    if hardware_observation_decision and phase_status != "stopped":
        hardware_action = optional_str(
            hardware_observation_decision, "recommended_next_action", "unknown"
        )
        if hardware_action == "stop_candidate_index_structural_profiling":
            phase_status = "stopped"
            current_focus = None
            recommended_next_action = hardware_action
            stop_reason = "no_stable_structural_signal"

    structural_inputs = {
        "branch_rollup_decision": str(branch_rollup_path),
        "candidate_index_operation_rollup_decision": (
            str(operation_rollup_path) if operation_rollup_path is not None else None
        ),
        "candidate_index_common_memory_behavior_decision": (
            str(common_memory_path) if common_memory_path is not None else None
        ),
        "candidate_index_hardware_observation_decision": (
            str(hardware_observation_path) if hardware_observation_path is not None else None
        ),
    }

    summary = {
        "decision_status": "ready",
        "phase": "candidate_index_structural_profiling",
        "phase_status": phase_status,
        "current_focus": current_focus,
        "recommended_next_action": recommended_next_action,
        "optional_next_action": optional_next_action,
        "stop_reason": stop_reason,
        "runtime_prototype_allowed": False,
        "authoritative_next_action_source": "branch_rollup_decision",
        "decision_context_status": "ready_but_requires_branch_rollup_context",
        "structural_inputs": structural_inputs,
    }
    return summary


def render_markdown(summary):
    lines = [
        "# Candidate-Index Structural Phase",
        "",
        f"- phase: `{summary['phase']}`",
        f"- phase_status: `{summary['phase_status']}`",
        f"- current_focus: `{summary.get('current_focus') or 'none'}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- optional_next_action: `{summary.get('optional_next_action') or 'none'}`",
        f"- stop_reason: `{summary.get('stop_reason') or 'none'}`",
        f"- runtime_prototype_allowed: `{str(summary['runtime_prototype_allowed']).lower()}`",
        f"- authoritative_next_action_source: `{summary['authoritative_next_action_source']}`",
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    branch_rollup_decision, branch_rollup_path = read_json(args.branch_rollup_decision)
    operation_rollup_decision, operation_rollup_path = (
        read_json(args.candidate_index_operation_rollup_decision)
        if args.candidate_index_operation_rollup_decision
        else ({}, None)
    )
    common_memory_decision, common_memory_path = (
        read_json(args.candidate_index_common_memory_behavior_decision)
        if args.candidate_index_common_memory_behavior_decision
        else ({}, None)
    )
    hardware_observation_decision, hardware_observation_path = (
        read_json(args.candidate_index_hardware_observation_decision)
        if args.candidate_index_hardware_observation_decision
        else ({}, None)
    )

    summary = build_summary(
        branch_rollup_decision,
        branch_rollup_path,
        operation_rollup_decision,
        operation_rollup_path,
        common_memory_decision,
        common_memory_path,
        hardware_observation_decision,
        hardware_observation_path,
    )
    decision = dict(summary)

    with (output_dir / "candidate_index_structural_phase_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "candidate_index_structural_phase_decision.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    (output_dir / "candidate_index_structural_phase_summary.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
