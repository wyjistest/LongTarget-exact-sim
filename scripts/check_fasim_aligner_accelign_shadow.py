#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Iterable


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    ModeSpec,
    RunResult,
    WorkloadSpec,
    run_once,
)
from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)


REQUIRED_KEYS = [
    "fasim_aligner_accelign_shadow_enabled",
    "fasim_aligner_accelign_shadow_supported",
    "fasim_aligner_accelign_shadow_disabled_reason",
    "fasim_aligner_accelign_shadow_requests_total",
    "fasim_aligner_accelign_shadow_requests_compared",
    "fasim_aligner_accelign_shadow_requests_unsupported",
    "fasim_aligner_accelign_shadow_query_bases",
    "fasim_aligner_accelign_shadow_target_bases",
    "fasim_aligner_accelign_shadow_cells",
    "fasim_aligner_accelign_shadow_h2d_bytes",
    "fasim_aligner_accelign_shadow_d2h_bytes",
    "fasim_aligner_accelign_shadow_kernel_seconds",
    "fasim_aligner_accelign_shadow_total_seconds",
    "fasim_aligner_accelign_shadow_cpu_reference_seconds",
    "fasim_aligner_accelign_shadow_score_mismatches",
    "fasim_aligner_accelign_shadow_endpoint_mismatches",
    "fasim_aligner_accelign_shadow_total_mismatches",
    "fasim_aligner_accelign_shadow_fallbacks",
    "fasim_aligner_accelign_shadow_has_score_contract",
    "fasim_aligner_accelign_shadow_has_endpoint_contract",
    "fasim_aligner_accelign_shadow_has_cigar_contract",
    "fasim_aligner_accelign_shadow_has_alignment_string_contract",
    "fasim_aligner_accelign_shadow_uses_runtime_output",
]

SCORE_ONLY_REQUIRED_KEYS = [
    "fasim_accelign_score_only_shadow_enabled",
    "fasim_accelign_score_only_mode",
    "fasim_accelign_score_only_requests",
    "fasim_accelign_score_only_requests_compared",
    "fasim_accelign_score_only_score_mismatches",
    "fasim_accelign_score_only_cpu_seconds",
    "fasim_accelign_score_only_kernel_seconds",
    "fasim_accelign_score_only_total_seconds",
    "fasim_accelign_score_only_h2d_bytes",
    "fasim_accelign_score_only_d2h_bytes",
    "fasim_accelign_score_only_query_reuse_active",
    "fasim_accelign_score_only_query_staging_bytes",
    "fasim_accelign_score_only_target_staging_bytes",
    "fasim_accelign_score_only_has_endpoint_contract",
    "fasim_accelign_score_only_uses_runtime_output",
]

SCORE_PRECHECK_REQUIRED_KEYS = [
    "fasim_accelign_score_precheck_shadow_enabled",
    "fasim_accelign_score_precheck_requests",
    "fasim_accelign_score_precheck_requests_compared",
    "fasim_accelign_score_precheck_score_mismatches",
    "fasim_accelign_score_precheck_predicted_reject",
    "fasim_accelign_score_precheck_true_reject",
    "fasim_accelign_score_precheck_false_reject",
    "fasim_accelign_score_precheck_false_keep",
    "fasim_accelign_score_precheck_predicted_reject_candidates",
    "fasim_accelign_score_precheck_false_reject_candidates",
    "fasim_accelign_score_precheck_est_cpu_align_calls_saved",
    "fasim_accelign_score_precheck_est_cpu_align_seconds_saved",
    "fasim_accelign_score_precheck_accelign_seconds",
    "fasim_accelign_score_precheck_net_est_seconds_saved",
    "fasim_accelign_score_precheck_query_reuse_active",
    "fasim_accelign_score_precheck_output_digest_affected",
    "fasim_accelign_score_precheck_has_endpoint_contract",
    "fasim_accelign_score_precheck_uses_runtime_output",
]

CALL_PRECHECK_REQUIRED_KEYS = [
    "fasim_accelign_call_precheck_shadow_enabled",
    "fasim_accelign_call_precheck_requests",
    "fasim_accelign_call_precheck_requests_compared",
    "fasim_accelign_call_precheck_score_mismatches",
    "fasim_accelign_call_precheck_predicted_skip_calls",
    "fasim_accelign_call_precheck_false_reject_calls",
    "fasim_accelign_call_precheck_false_reject_candidates",
    "fasim_accelign_call_precheck_candidate_state_mismatches",
    "fasim_accelign_call_precheck_emitted_record_mismatches",
    "fasim_accelign_call_precheck_output_digest_mismatches",
    "fasim_accelign_call_precheck_est_cpu_seconds_saved",
    "fasim_accelign_call_precheck_accelign_seconds",
    "fasim_accelign_call_precheck_net_est_seconds_saved",
    "fasim_accelign_call_precheck_projected_full_saved",
    "fasim_accelign_call_precheck_has_endpoint_contract",
    "fasim_accelign_call_precheck_uses_runtime_output",
]

ENDPOINT_ENVELOPE_REQUIRED_KEYS = [
    "fasim_accelign_endpoint_envelope_shadow_enabled",
    "fasim_accelign_endpoint_envelope_shadow_requests",
    "fasim_accelign_endpoint_envelope_shadow_requests_compared",
    "fasim_accelign_endpoint_envelope_shadow_requests_unsupported",
    "fasim_accelign_endpoint_envelope_shadow_flank",
    "fasim_accelign_endpoint_envelope_shadow_score_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_endpoint_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_cigar_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_alignment_string_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_total_mismatches",
    "fasim_accelign_endpoint_envelope_shadow_contains_cpu_endpoint",
    "fasim_accelign_endpoint_envelope_shadow_misses_cpu_endpoint",
    "fasim_accelign_endpoint_envelope_shadow_contains_cpu_interval",
    "fasim_accelign_endpoint_envelope_shadow_misses_cpu_interval",
    "fasim_accelign_endpoint_envelope_shadow_accelign_seconds",
    "fasim_accelign_endpoint_envelope_shadow_cpu_full_seconds",
    "fasim_accelign_endpoint_envelope_shadow_cpu_envelope_seconds",
    "fasim_accelign_endpoint_envelope_shadow_net_est_seconds_saved",
    "fasim_accelign_endpoint_envelope_shadow_projected_full_saved",
    "fasim_accelign_endpoint_envelope_shadow_has_score_contract",
    "fasim_accelign_endpoint_envelope_shadow_has_endpoint_contract",
    "fasim_accelign_endpoint_envelope_shadow_has_cigar_contract",
    "fasim_accelign_endpoint_envelope_shadow_has_alignment_string_contract",
    "fasim_accelign_endpoint_envelope_shadow_uses_runtime_output",
]


def metric_float(metrics: Dict[str, str], key: str) -> float:
    try:
        return float(metrics[key])
    except KeyError as exc:
        raise RuntimeError(f"missing metric {key}") from exc
    except ValueError as exc:
        raise RuntimeError(f"non-numeric metric {key}={metrics[key]!r}") from exc


def metric_int(metrics: Dict[str, str], key: str) -> int:
    return int(round(metric_float(metrics, key)))


def require_metrics(metrics: Dict[str, str], keys: Iterable[str]) -> None:
    for key in keys:
        metric_float(metrics, key)


def require_digest_match(table: RunResult, observed: RunResult, label: str) -> None:
    if table.digest != observed.digest:
        raise RuntimeError(f"{label}: digest mismatch: {table.digest} vs {observed.digest}")
    if table.records != observed.records:
        raise RuntimeError(f"{label}: record mismatch: {table.records} vs {observed.records}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_aligner_accelign_shadow"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir)
    fixture_dir = work_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    dna_path = fixture_dir / "hg38_chr21_softmask_compact_region.fa"
    write_fasta(
        dna_path,
        "hg38|chr21|41825001-41830000",
        decode_fixture(HG38_CHR21_SOFTMASK_COMPACT_REGION_Z),
    )
    workload = WorkloadSpec(
        "hg38_chr21_softmask_compact_region",
        "small hg38 soft-mask fixture with Accelign shadow coverage",
        dna_path=dna_path,
        rna_path=ROOT / "H19.fa",
    )

    table = run_once(
        workload=workload,
        mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "table_only",
        require_profile=True,
    )
    shadow = run_once(
        workload=workload,
        mode=ModeSpec(
            "accelign_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ACCELIGN_SHADOW": "1",
                "FASIM_ALIGNER_ACCELIGN_SHADOW_MAX_REQUESTS": "256",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "accelign_shadow",
        require_profile=True,
    )
    require_digest_match(table, shadow, "accelign_shadow")
    require_metrics(shadow.metrics, REQUIRED_KEYS)

    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_enabled") != 1:
        raise RuntimeError("Accelign shadow was not enabled")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_supported") != 1:
        raise RuntimeError("Accelign shadow backend was not supported")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_uses_runtime_output") != 0:
        raise RuntimeError("Accelign shadow must not feed runtime output")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_requests_total") <= 0:
        raise RuntimeError("Accelign shadow did not observe any requests")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_requests_compared") <= 0:
        raise RuntimeError("Accelign shadow did not compare any requests")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_h2d_bytes") <= 0:
        raise RuntimeError("Accelign shadow did not transfer request bytes to GPU")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_d2h_bytes") <= 0:
        raise RuntimeError("Accelign shadow did not transfer result bytes from GPU")
    if metric_float(shadow.metrics, "fasim_aligner_accelign_shadow_kernel_seconds") <= 0.0:
        raise RuntimeError("Accelign shadow did not report GPU kernel time")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_has_score_contract") != 1:
        raise RuntimeError("Accelign shadow must report score contract coverage")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_score_mismatches") != 0:
        raise RuntimeError("Accelign shadow score contract mismatched")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_has_cigar_contract") != 0:
        raise RuntimeError("Accelign shadow must not claim CIGAR coverage")
    if metric_int(shadow.metrics, "fasim_aligner_accelign_shadow_has_alignment_string_contract") != 0:
        raise RuntimeError("Accelign shadow must not claim alignment-string coverage")

    score_only = run_once(
        workload=workload,
        mode=ModeSpec(
            "accelign_score_only_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ACCELIGN_SCORE_ONLY_SHADOW": "1",
                "FASIM_ALIGNER_ACCELIGN_SCORE_ONLY_SHADOW_MAX_REQUESTS": "256",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "accelign_score_only_shadow",
        require_profile=True,
    )
    require_digest_match(table, score_only, "accelign_score_only_shadow")
    require_metrics(score_only.metrics, SCORE_ONLY_REQUIRED_KEYS)

    if metric_int(score_only.metrics, "fasim_accelign_score_only_shadow_enabled") != 1:
        raise RuntimeError("Accelign score-only shadow was not enabled")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_requests") <= 0:
        raise RuntimeError("Accelign score-only shadow did not compare any requests")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_requests_compared") <= 0:
        raise RuntimeError("Accelign score-only shadow did not compare any sampled requests")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_uses_runtime_output") != 0:
        raise RuntimeError("Accelign score-only shadow must not feed runtime output")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_has_endpoint_contract") != 0:
        raise RuntimeError("Accelign score-only shadow must not claim endpoint coverage")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_score_mismatches") != 0:
        raise RuntimeError("Accelign score-only shadow score contract mismatched")
    if metric_float(score_only.metrics, "fasim_accelign_score_only_cpu_seconds") <= 0.0:
        raise RuntimeError("Accelign score-only shadow did not report CPU reference time")
    if metric_float(score_only.metrics, "fasim_accelign_score_only_kernel_seconds") <= 0.0:
        raise RuntimeError("Accelign score-only shadow did not report GPU kernel time")
    if metric_float(score_only.metrics, "fasim_accelign_score_only_total_seconds") <= 0.0:
        raise RuntimeError("Accelign score-only shadow did not report total time")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_h2d_bytes") <= 0:
        raise RuntimeError("Accelign score-only shadow did not report H2D bytes")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_d2h_bytes") <= 0:
        raise RuntimeError("Accelign score-only shadow did not report D2H bytes")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_query_staging_bytes") <= 0:
        raise RuntimeError("Accelign score-only shadow did not report query staging bytes")
    if metric_int(score_only.metrics, "fasim_accelign_score_only_target_staging_bytes") <= 0:
        raise RuntimeError("Accelign score-only shadow did not report target staging bytes")

    precheck = run_once(
        workload=workload,
        mode=ModeSpec(
            "accelign_score_precheck_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_SHADOW": "1",
                "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_SHADOW_MAX_REQUESTS": "256",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "accelign_score_precheck_shadow",
        require_profile=True,
    )
    require_digest_match(table, precheck, "accelign_score_precheck_shadow")
    require_metrics(precheck.metrics, SCORE_PRECHECK_REQUIRED_KEYS)

    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_shadow_enabled") != 1:
        raise RuntimeError("Accelign score precheck shadow was not enabled")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_requests") <= 0:
        raise RuntimeError("Accelign score precheck shadow did not observe requests")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_requests_compared") <= 0:
        raise RuntimeError("Accelign score precheck shadow did not compare requests")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_uses_runtime_output") != 0:
        raise RuntimeError("Accelign score precheck shadow must not feed runtime output")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_has_endpoint_contract") != 0:
        raise RuntimeError("Accelign score precheck shadow must not use endpoint contract")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_score_mismatches") != 0:
        raise RuntimeError("Accelign score precheck score contract mismatched")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_false_reject") != 0:
        raise RuntimeError("Accelign score precheck would false-reject a CPU score-pass call")
    if metric_int(precheck.metrics, "fasim_accelign_score_precheck_output_digest_affected") != 0:
        raise RuntimeError("Accelign score precheck shadow must not affect output digest")
    if metric_float(precheck.metrics, "fasim_accelign_score_precheck_accelign_seconds") <= 0.0:
        raise RuntimeError("Accelign score precheck did not report Accelign seconds")
    saved_seconds = metric_float(
        precheck.metrics, "fasim_accelign_score_precheck_est_cpu_align_seconds_saved"
    )
    accelign_seconds = metric_float(precheck.metrics, "fasim_accelign_score_precheck_accelign_seconds")
    net_seconds = metric_float(precheck.metrics, "fasim_accelign_score_precheck_net_est_seconds_saved")
    if abs(net_seconds - (saved_seconds - accelign_seconds)) > 0.0001:
        raise RuntimeError(
            "Accelign score precheck net estimate must equal saved CPU seconds minus Accelign seconds"
        )

    call_precheck = run_once(
        workload=workload,
        mode=ModeSpec(
            "accelign_call_precheck_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_CONTRACT_SHADOW": "1",
                "FASIM_ALIGNER_ACCELIGN_SCORE_PRECHECK_SHADOW_MAX_REQUESTS": "256",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "accelign_call_precheck_shadow",
        require_profile=True,
    )
    require_digest_match(table, call_precheck, "accelign_call_precheck_shadow")
    require_metrics(call_precheck.metrics, CALL_PRECHECK_REQUIRED_KEYS)

    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_shadow_enabled") != 1:
        raise RuntimeError("Accelign call-level precheck contract shadow was not enabled")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_requests") <= 0:
        raise RuntimeError("Accelign call-level precheck did not observe requests")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_requests_compared") <= 0:
        raise RuntimeError("Accelign call-level precheck did not compare sampled requests")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_score_mismatches") != 0:
        raise RuntimeError("Accelign call-level precheck score contract mismatched")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_has_endpoint_contract") != 0:
        raise RuntimeError("Accelign call-level precheck must not use endpoint contract")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_uses_runtime_output") != 0:
        raise RuntimeError("Accelign call-level precheck must not feed runtime output")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_false_reject_calls") != 0:
        raise RuntimeError("Accelign call-level precheck would skip a CPU score-pass call")
    if metric_int(call_precheck.metrics, "fasim_accelign_call_precheck_output_digest_mismatches") != 0:
        raise RuntimeError("Accelign call-level precheck shadow must not affect output digest")
    if metric_float(call_precheck.metrics, "fasim_accelign_call_precheck_accelign_seconds") <= 0.0:
        raise RuntimeError("Accelign call-level precheck did not report Accelign seconds")
    saved_seconds = metric_float(
        call_precheck.metrics, "fasim_accelign_call_precheck_est_cpu_seconds_saved"
    )
    accelign_seconds = metric_float(
        call_precheck.metrics, "fasim_accelign_call_precheck_accelign_seconds"
    )
    net_seconds = metric_float(
        call_precheck.metrics, "fasim_accelign_call_precheck_net_est_seconds_saved"
    )
    if abs(net_seconds - (saved_seconds - accelign_seconds)) > 0.0001:
        raise RuntimeError(
            "Accelign call-level precheck net estimate must equal saved CPU seconds minus Accelign seconds"
        )

    endpoint_envelope = run_once(
        workload=workload,
        mode=ModeSpec(
            "accelign_endpoint_envelope_shadow",
            "cuda",
            {
                "FASIM_TRANSFERSTRING_TABLE": "1",
                "FASIM_GPU_DP_COLUMN_AUTO": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW": "1",
                "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW_MAX_REQUESTS": "256",
                "FASIM_ALIGNER_ACCELIGN_ENDPOINT_ENVELOPE_SHADOW_FLANK": "64",
            },
        ),
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / "accelign_endpoint_envelope_shadow",
        require_profile=True,
    )
    require_digest_match(table, endpoint_envelope, "accelign_endpoint_envelope_shadow")
    require_metrics(endpoint_envelope.metrics, ENDPOINT_ENVELOPE_REQUIRED_KEYS)

    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_enabled") != 1:
        raise RuntimeError("Accelign endpoint-envelope shadow was not enabled")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_requests") <= 0:
        raise RuntimeError("Accelign endpoint-envelope shadow did not observe requests")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_requests_compared") <= 0:
        raise RuntimeError("Accelign endpoint-envelope shadow did not compare requests")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_flank") != 64:
        raise RuntimeError("Accelign endpoint-envelope flank telemetry did not match env")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_uses_runtime_output") != 0:
        raise RuntimeError("Accelign endpoint-envelope shadow must not feed runtime output")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_has_score_contract") != 1:
        raise RuntimeError("Accelign endpoint-envelope shadow must compare scores")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_has_endpoint_contract") != 1:
        raise RuntimeError("Accelign endpoint-envelope shadow must compare endpoints")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_has_cigar_contract") != 1:
        raise RuntimeError("Accelign endpoint-envelope shadow must compare CIGAR")
    if metric_int(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_has_alignment_string_contract") != 0:
        raise RuntimeError("Accelign endpoint-envelope shadow must not claim materialized alignment strings")
    if metric_float(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_accelign_seconds") <= 0.0:
        raise RuntimeError("Accelign endpoint-envelope shadow did not report Accelign time")
    if metric_float(endpoint_envelope.metrics, "fasim_accelign_endpoint_envelope_shadow_cpu_envelope_seconds") <= 0.0:
        raise RuntimeError("Accelign endpoint-envelope shadow did not report CPU envelope time")

    print("Fasim Accelign aligner shadow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
