#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Dict, Iterable, List, Tuple


TRANSFER_STRING_REQUIRED_FIELDS = [
    "fasim_transfer_string_seconds",
    "fasim_transfer_string_calls",
    "fasim_transfer_string_input_bases",
    "fasim_transfer_string_output_bases",
    "fasim_transfer_string_rule_select_seconds",
    "fasim_transfer_string_rule_materialize_seconds",
    "fasim_transfer_string_convert_seconds",
    "fasim_transfer_string_validate_seconds",
    "fasim_transfer_string_residual_seconds",
    "fasim_transfer_string_para_forward_calls",
    "fasim_transfer_string_para_forward_seconds",
    "fasim_transfer_string_para_reverse_calls",
    "fasim_transfer_string_para_reverse_seconds",
    "fasim_transfer_string_anti_forward_calls",
    "fasim_transfer_string_anti_forward_seconds",
    "fasim_transfer_string_anti_reverse_calls",
    "fasim_transfer_string_anti_reverse_seconds",
    "fasim_transfer_string_table_shadow_enabled",
    "fasim_transfer_string_table_shadow_calls",
    "fasim_transfer_string_table_shadow_compared_calls",
    "fasim_transfer_string_table_shadow_mismatches",
    "fasim_transfer_string_table_shadow_fallbacks",
    "fasim_transfer_string_table_shadow_seconds",
    "fasim_transfer_string_table_shadow_input_bases",
    "fasim_transfer_string_table_requested",
    "fasim_transfer_string_table_active",
    "fasim_transfer_string_table_validate_enabled",
    "fasim_transfer_string_table_calls",
    "fasim_transfer_string_table_seconds",
    "fasim_transfer_string_table_legacy_validate_seconds",
    "fasim_transfer_string_table_compared",
    "fasim_transfer_string_table_mismatches",
    "fasim_transfer_string_table_fallbacks",
    "fasim_transfer_string_table_bases_converted",
] + [
    f"fasim_transfer_string_rule_{rule}_calls"
    for rule in range(1, 19)
] + [
    f"fasim_transfer_string_rule_{rule}_seconds"
    for rule in range(1, 19)
]


GPU_DP_COLUMN_REQUIRED_FIELDS = [
    "fasim_gpu_dp_column_requested",
    "fasim_gpu_dp_column_active",
    "fasim_gpu_dp_column_validate_enabled",
    "fasim_gpu_dp_column_calls",
    "fasim_gpu_dp_column_windows",
    "fasim_gpu_dp_column_cells",
    "fasim_gpu_dp_column_h2d_bytes",
    "fasim_gpu_dp_column_d2h_bytes",
    "fasim_gpu_dp_column_kernel_seconds",
    "fasim_gpu_dp_column_total_seconds",
    "fasim_gpu_dp_column_validate_seconds",
    "fasim_gpu_dp_column_topk_cap",
    "fasim_gpu_dp_column_score_mismatches",
    "fasim_gpu_dp_column_column_max_mismatches",
    "fasim_gpu_dp_column_fallbacks",
    "fasim_gpu_dp_column_debug_enabled",
    "fasim_gpu_dp_column_first_mismatch_window",
    "fasim_gpu_dp_column_first_mismatch_column",
    "fasim_gpu_dp_column_first_mismatch_cpu_score",
    "fasim_gpu_dp_column_first_mismatch_gpu_score",
    "fasim_gpu_dp_column_first_mismatch_cpu_position",
    "fasim_gpu_dp_column_first_mismatch_gpu_position",
    "fasim_gpu_dp_column_first_mismatch_cpu_count",
    "fasim_gpu_dp_column_first_mismatch_gpu_count",
    "fasim_gpu_dp_column_first_mismatch_tie",
    "fasim_gpu_dp_column_cpu_scoreinfo_score",
    "fasim_gpu_dp_column_gpu_scoreinfo_score",
    "fasim_gpu_dp_column_cpu_scoreinfo_position",
    "fasim_gpu_dp_column_gpu_scoreinfo_position",
    "fasim_gpu_dp_column_scoreinfo_field_mismatch_mask",
    "fasim_gpu_dp_column_score_delta_max",
    "fasim_gpu_dp_column_scoreinfo_mismatches",
    "fasim_gpu_dp_column_tie_mismatches",
    "fasim_gpu_dp_column_position_mismatches",
    "fasim_gpu_dp_column_topk_truncated_windows",
    "fasim_gpu_dp_column_topk_overflow_windows",
    "fasim_gpu_dp_column_pre_topk_mismatches",
    "fasim_gpu_dp_column_post_topk_mismatches",
    "fasim_gpu_dp_column_debug_windows_examined",
]


REQUIRED_PROFILE_FIELDS = [
    "fasim_total_seconds",
    "fasim_io_seconds",
    "fasim_window_generation_seconds",
    "fasim_window_generation_cut_sequence_seconds",
    "fasim_window_generation_transfer_seconds",
    "fasim_window_generation_reverse_seconds",
    "fasim_window_generation_source_transform_seconds",
    "fasim_window_generation_encode_seconds",
    "fasim_window_generation_flush_seconds",
    "fasim_dp_scoring_seconds",
    "fasim_column_max_seconds",
    "fasim_local_max_seconds",
    "fasim_nonoverlap_seconds",
    "fasim_validation_seconds",
    "fasim_output_seconds",
    "fasim_num_queries",
    "fasim_num_windows",
    "fasim_num_dp_cells",
    "fasim_num_candidates",
    "fasim_num_validated_candidates",
    "fasim_num_final_hits",
] + TRANSFER_STRING_REQUIRED_FIELDS + GPU_DP_COLUMN_REQUIRED_FIELDS


WINDOW_GENERATION_DETAIL_KEYS = [
    ("cutSequence", "fasim_window_generation_cut_sequence_seconds"),
    ("transferString", "fasim_window_generation_transfer_seconds"),
    ("reverse/complement", "fasim_window_generation_reverse_seconds"),
    ("source transform", "fasim_window_generation_source_transform_seconds"),
    ("encoded target build", "fasim_window_generation_encode_seconds"),
    ("flush_batch call wall", "fasim_window_generation_flush_seconds"),
]


TRANSFER_STRING_STEP_KEYS = [
    ("rule select", "fasim_transfer_string_rule_select_seconds"),
    ("rule materialize", "fasim_transfer_string_rule_materialize_seconds"),
    ("per-base convert", "fasim_transfer_string_convert_seconds"),
    ("validate", "fasim_transfer_string_validate_seconds"),
    ("copy/return residual", "fasim_transfer_string_residual_seconds"),
]


TRANSFER_STRING_MODE_KEYS = [
    ("para forward", "fasim_transfer_string_para_forward_calls", "fasim_transfer_string_para_forward_seconds"),
    ("para reverse", "fasim_transfer_string_para_reverse_calls", "fasim_transfer_string_para_reverse_seconds"),
    ("anti forward", "fasim_transfer_string_anti_forward_calls", "fasim_transfer_string_anti_forward_seconds"),
    ("anti reverse", "fasim_transfer_string_anti_reverse_calls", "fasim_transfer_string_anti_reverse_seconds"),
]


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def parse_benchmark_metrics(stderr: str) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("benchmark."):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        metrics[key[len("benchmark.") :]] = value
    return metrics


def canonical_lite_records(output_dir: Path) -> List[str]:
    records: List[str] = []
    paths = sorted(output_dir.glob("*-TFOsorted.lite"))
    if not paths:
        raise RuntimeError(f"missing Fasim lite output in {output_dir}")
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_no, line in enumerate(handle):
                line = line.rstrip("\n").rstrip("\r")
                if not line:
                    continue
                if line_no == 0 and line.startswith("Chr\tStartInGenome\t"):
                    continue
                records.append(line)
    records.sort()
    return records


def digest_records(records: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.encode("utf-8"))
        digest.update(b"\n")
    return "sha256:" + digest.hexdigest()


def read_expected_digest(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"empty expected digest file: {path}")
    return value


def run_fasim(root: Path, bin_path: Path, work_dir: Path) -> Tuple[str, str, Path]:
    if not bin_path.exists():
        raise RuntimeError(f"missing Fasim binary: {bin_path}")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    input_dir = work_dir / "inputs"
    output_dir = work_dir / "out"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    shutil.copy(root / "testDNA.fa", input_dir / "testDNA.fa")
    shutil.copy(root / "H19.fa", input_dir / "H19.fa")

    env = os.environ.copy()
    env["FASIM_VERBOSE"] = "0"
    env["FASIM_OUTPUT_MODE"] = "lite"
    env["FASIM_PROFILE"] = "1"
    env["FASIM_EXTEND_THREADS"] = "1"

    cmd = [
        str(bin_path),
        "-f1",
        "testDNA.fa",
        "-f2",
        "H19.fa",
        "-r",
        "1",
        "-O",
        str(output_dir),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(input_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    (work_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (work_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"Fasim exited with {proc.returncode}; see {work_dir / 'stderr.log'}"
        )
    return proc.stdout, proc.stderr, output_dir


def metric_float(metrics: Dict[str, str], key: str) -> float:
    try:
        return float(metrics.get(key, "0"))
    except ValueError:
        return 0.0


def print_window_generation_detail_table(metrics: Dict[str, str]) -> None:
    total = metric_float(metrics, "fasim_total_seconds")
    print("Window generation detail:")
    print("")
    print("| Detail | Seconds | Percent of total |")
    print("| --- | ---: | ---: |")
    for label, key in WINDOW_GENERATION_DETAIL_KEYS:
        seconds = metric_float(metrics, key)
        percent = (seconds / total * 100.0) if total > 0 else 0.0
        print(f"| {label} | {seconds:.6f} | {percent:.2f}% |")
    print("")
    print(
        "Note: flush_batch call wall is diagnostic overlap with scoring/output; "
        "it is not included in fasim_window_generation_seconds."
    )


def print_transfer_string_detail_table(metrics: Dict[str, str]) -> None:
    transfer_total = metric_float(metrics, "fasim_transfer_string_seconds")
    calls = metrics.get("fasim_transfer_string_calls", "0")
    bases = metrics.get("fasim_transfer_string_input_bases", "0")

    print("transferString detail:")
    print("")
    print(f"calls: {calls}")
    print(f"input bases: {bases}")
    print("")
    print("| Step | Seconds | Percent of transferString |")
    print("| --- | ---: | ---: |")
    for label, key in TRANSFER_STRING_STEP_KEYS:
        seconds = metric_float(metrics, key)
        percent = (seconds / transfer_total * 100.0) if transfer_total > 0 else 0.0
        print(f"| {label} | {seconds:.6f} | {percent:.2f}% |")
    print("")
    print("| Mode | Calls | Seconds | Percent of transferString |")
    print("| --- | ---: | ---: | ---: |")
    for label, calls_key, seconds_key in TRANSFER_STRING_MODE_KEYS:
        mode_calls = metrics.get(calls_key, "0")
        seconds = metric_float(metrics, seconds_key)
        percent = (seconds / transfer_total * 100.0) if transfer_total > 0 else 0.0
        print(f"| {label} | {mode_calls} | {seconds:.6f} | {percent:.2f}% |")

    rule_rows = []
    for rule in range(1, 19):
        calls_value = metrics.get(f"fasim_transfer_string_rule_{rule}_calls", "0")
        seconds = metric_float(metrics, f"fasim_transfer_string_rule_{rule}_seconds")
        try:
            calls_int = int(calls_value)
        except ValueError:
            calls_int = 0
        if calls_int > 0 or seconds > 0:
            rule_rows.append((rule, calls_value, seconds))
    if rule_rows:
        print("")
        print("| Rule | Calls | Seconds | Percent of transferString |")
        print("| ---: | ---: | ---: | ---: |")
        for rule, calls_value, seconds in rule_rows:
            percent = (seconds / transfer_total * 100.0) if transfer_total > 0 else 0.0
            print(f"| {rule} | {calls_value} | {seconds:.6f} | {percent:.2f}% |")

    print("")
    print("transferString table shadow:")
    print("")
    print("| Metric | Value |")
    print("| --- | ---: |")
    for key in [
        "fasim_transfer_string_table_shadow_enabled",
        "fasim_transfer_string_table_shadow_calls",
        "fasim_transfer_string_table_shadow_compared_calls",
        "fasim_transfer_string_table_shadow_mismatches",
        "fasim_transfer_string_table_shadow_fallbacks",
        "fasim_transfer_string_table_shadow_seconds",
        "fasim_transfer_string_table_shadow_input_bases",
    ]:
        print(f"| {key} | {metrics.get(key, '0')} |")

    print("")
    print("transferString table opt-in:")
    print("")
    print("| Metric | Value |")
    print("| --- | ---: |")
    for key in [
        "fasim_transfer_string_table_requested",
        "fasim_transfer_string_table_active",
        "fasim_transfer_string_table_validate_enabled",
        "fasim_transfer_string_table_calls",
        "fasim_transfer_string_table_seconds",
        "fasim_transfer_string_table_legacy_validate_seconds",
        "fasim_transfer_string_table_compared",
        "fasim_transfer_string_table_mismatches",
        "fasim_transfer_string_table_fallbacks",
        "fasim_transfer_string_table_bases_converted",
    ]:
        print(f"| {key} | {metrics.get(key, '0')} |")

    print("")
    print("GPU DP+column prototype:")
    print("")
    print("| Metric | Value |")
    print("| --- | ---: |")
    for key in GPU_DP_COLUMN_REQUIRED_FIELDS:
        print(f"| {key} | {metrics.get(key, '0')} |")


def print_report(metrics: Dict[str, str], digest: str, record_count: int) -> None:
    total = metric_float(metrics, "fasim_total_seconds")
    dp = metric_float(metrics, "fasim_dp_scoring_seconds")
    column = metric_float(metrics, "fasim_column_max_seconds")
    local = metric_float(metrics, "fasim_local_max_seconds")
    gpu_candidate = dp + column + local
    dp_pct = (dp / total * 100.0) if total > 0 else 0.0
    gpu_candidate_pct = (gpu_candidate / total * 100.0) if total > 0 else 0.0

    print("Fasim acceleration feasibility profile")
    print("")
    print("| Stage | Seconds | Percent |")
    print("| --- | ---: | ---: |")
    stage_keys = [
        ("I/O", "fasim_io_seconds"),
        ("window generation", "fasim_window_generation_seconds"),
        ("DP scoring", "fasim_dp_scoring_seconds"),
        ("column max", "fasim_column_max_seconds"),
        ("local max", "fasim_local_max_seconds"),
        ("non-overlap", "fasim_nonoverlap_seconds"),
        ("validation", "fasim_validation_seconds"),
        ("output", "fasim_output_seconds"),
    ]
    for label, key in stage_keys:
        seconds = metric_float(metrics, key)
        percent = (seconds / total * 100.0) if total > 0 else 0.0
        print(f"| {label} | {seconds:.6f} | {percent:.2f}% |")
    print("")
    print_window_generation_detail_table(metrics)
    print("")
    print_transfer_string_detail_table(metrics)
    print("")
    print(f"DP/scoring percentage: {dp_pct:.2f}%")
    print(f"GPU-candidate percentage (DP + column + local): {gpu_candidate_pct:.2f}%")
    print(f"canonical output digest: {digest}")
    print(f"canonical output records: {record_count}")
    print("")
    print("| DP speedup | Amdahl total speedup | Estimated total seconds |")
    print("| ---: | ---: | ---: |")
    dp_fraction = (dp / total) if total > 0 else 0.0
    for speedup in (5, 10, 20, 50):
        total_speedup = 1.0 / ((1.0 - dp_fraction) + (dp_fraction / speedup)) if total > 0 else 0.0
        estimated_seconds = total / total_speedup if total_speedup > 0 else 0.0
        print(f"| {speedup}x | {total_speedup:.3f}x | {estimated_seconds:.6f} |")

    for key, value in sorted(metrics.items()):
        print(f"benchmark.{key}={value}")
    print("benchmark.fasim_output_digest_available=1")
    print(f"benchmark.fasim_output_digest={digest}")
    print(f"benchmark.fasim_canonical_output_records={record_count}")
    print(f"benchmark.fasim_dp_scoring_percent={dp_pct:.6f}")
    print(f"benchmark.fasim_gpu_candidate_percent={gpu_candidate_pct:.6f}")


def validate_profile(metrics: Dict[str, str]) -> None:
    missing = [key for key in REQUIRED_PROFILE_FIELDS if key not in metrics]
    if missing:
        raise RuntimeError("missing Fasim profile metrics: " + ", ".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("exactness", "profile"), required=True)
    parser.add_argument("--bin", required=True)
    parser.add_argument("--expected-digest-file")
    parser.add_argument("--require-profile", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--work-dir")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    bin_path = Path(args.bin)
    if not bin_path.is_absolute():
        bin_path = (root / bin_path).resolve()
    work_dir_base = Path(args.work_dir) if args.work_dir else root / ".tmp" / "fasim_acceleration_feasibility" / args.mode
    repeat = args.repeat if args.repeat > 0 else 1

    try:
        last_metrics: Dict[str, str] = {}
        last_digest = ""
        last_record_count = 0
        seen_digests: List[str] = []
        expected = read_expected_digest(Path(args.expected_digest_file)) if args.expected_digest_file else None
        for run_index in range(repeat):
            work_dir = work_dir_base if repeat == 1 else work_dir_base / f"run{run_index + 1}"
            _, stderr, output_dir = run_fasim(root, bin_path, work_dir)
            metrics = parse_benchmark_metrics(stderr)
            if args.require_profile or args.mode == "profile":
                validate_profile(metrics)

            records = canonical_lite_records(output_dir)
            digest = digest_records(records)
            if expected is not None and digest != expected:
                raise RuntimeError(f"canonical digest mismatch: expected {expected}, got {digest}")
            seen_digests.append(digest)
            if digest != seen_digests[0]:
                raise RuntimeError(
                    f"canonical digest changed across repeats: {seen_digests[0]} vs {digest}"
                )
            last_metrics = metrics
            last_digest = digest
            last_record_count = len(records)

        print_report(last_metrics, last_digest, last_record_count)
        return 0
    except Exception as exc:
        eprint(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
