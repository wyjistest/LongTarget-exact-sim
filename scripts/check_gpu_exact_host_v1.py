#!/usr/bin/env python3
"""Compare isolated host optimizations against a frozen cross-task binary."""
import argparse
import json
import os
from pathlib import Path
import statistics

from check_gpu_exact_repair_v1 import run, sha
from check_gpu_exact_batch_v1 import (
    REPAIR, PREFIX, frozen_case, full_case, compare_consumers,
    gpu_snapshot, gpu_process_snapshot, write_json)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=('panel', 'full', 'benchmark', 'profile', 'faults'), required=True)
    p.add_argument('--reuse-query', action='store_true')
    p.add_argument('--gpu', default='GPU-d1f5be95-b8a3-3c18-f919-90913038a1a3')
    args = p.parse_args()
    if args.stage == 'faults' and not args.reuse_query:
        p.error('faults stage checks the opt-in query-reuse prerequisites; use --reuse-query')
    args.binary, args.baseline, args.work = (
        path.resolve() for path in (args.binary, args.baseline, args.work))
    args.work.mkdir(parents=True, exist_ok=False)
    if args.stage == 'panel':
        specs = [frozen_case(name, REPAIR / 'scoreinfo03' / name)
                 for name in ('prefix5000', 'affected_locus')]
        specs += [frozen_case(name, REPAIR / 'panel04' / name)
                  for name in ('H19', 'v2p4_w001', 'v2p4_w003', 'v2p4_w007')]
        specs += [frozen_case(name, REPAIR / 'panel05' / name)
                  for name in ('ENSG00000229613', 'ENSG00000267107', 'ENSG00000271913')]
    else:
        specs = [full_case()]
    order = ['control', 'candidate', 'candidate', 'control'] if args.stage == 'benchmark' else ['candidate']
    write_json(args.work / 'plan.json', dict(
        stage=args.stage, candidate=str(args.binary), candidate_sha256=sha(args.binary),
        baseline=str(args.baseline), baseline_sha256=sha(args.baseline),
        candidate_query_reuse=args.reuse_query, order=order, fixtures=specs,
        affinity=sorted(os.sched_getaffinity(0)), load_average=os.getloadavg(),
        gpu_snapshot=gpu_snapshot(), gpu_processes=gpu_process_snapshot(),
        limitation='reused development inputs; no paper acceptance or OpenMP comparison'))
    results = []
    faults = [('missing_batch', {'FASIM_GPU_EXACT_BATCH_V1': '0'}),
              ('missing_repair', {'FASIM_GPU_EXACT_REPAIR_V1': '0'}),
              ('no_gpu', {'CUDA_VISIBLE_DEVICES': ''}),
              ('capacity', {'FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_MAX_PER_TASK': '1'})]
    for spec in specs:
        runs = [(name, 'candidate', env) for name, env in faults] if args.stage == 'faults' else [
            ('%02d_%s' % (i, arm) if args.stage == 'benchmark' else spec['label'], arm, {})
            for i, arm in enumerate(order)]
        for name, arm, overrides in runs:
            directory = args.work / name
            env = {'FASIM_GPU_EXACT_BATCH_V1': '1',
                   'FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH': '4096',
                   'FASIM_GPU_EXACT_QUERY_REUSE_V1': '1' if args.reuse_query and arm == 'candidate' else '0'}
            if args.stage == 'profile':
                env['FASIM_SSW_CUDA_PHASE1_PROFILE'] = '1'
            if args.stage == 'panel':
                env['FASIM_GPU_EXACT_REPAIR_CHECK_SCOREINFO'] = '1'
            env.update(overrides)
            report = args.stage not in ('benchmark', 'faults')
            receipt = run(args.baseline if arm == 'control' else args.binary,
                          Path(spec['query']), Path(spec['target']), directory,
                          args.gpu, True, 1800, env, report=report,
                          expect_failure=args.stage == 'faults')
            result = dict(label=name, arm=arm, wall_seconds=receipt['wall_seconds'],
                          returncode=receipt['returncode'])
            if args.stage != 'faults':
                if receipt.get('output_sha256') != spec['reference_sha256']:
                    raise RuntimeError('output mismatch: ' + name)
                if receipt['metrics'].get(PREFIX + 'active') != '1':
                    raise RuntimeError('cross-task batching inactive')
                if args.reuse_query and arm == 'candidate' and int(receipt['metrics'].get(
                        PREFIX + 'cpu_query_prepares', '0')) <= 0:
                    raise RuntimeError('prepared query path inactive')
                result.update(byte_equal=True, output_sha256=receipt['output_sha256'],
                              batch={k[len(PREFIX):]: v for k, v in receipt['metrics'].items()
                                     if k.startswith(PREFIX)})
                if report:
                    result['consumer_comparison'] = compare_consumers(
                        Path(spec['consumer_reference']), directory / 'consumer.tsv', receipt['metrics'])
            results.append(result)
            write_json(directory / 'comparison.json', result)
            write_json(args.work / 'progress.json', results)
    if args.stage == 'benchmark':
        control = [r['wall_seconds'] for r in results if r['arm'] == 'control']
        candidate = [r['wall_seconds'] for r in results if r['arm'] == 'candidate']
        write_json(args.work / 'performance.json', dict(
            control_wall_seconds=control, candidate_wall_seconds=candidate,
            control_median_seconds=statistics.median(control),
            candidate_median_seconds=statistics.median(candidate),
            median_additional_speedup=statistics.median(control) / statistics.median(candidate),
            wall_reduction_fraction=1 - statistics.median(candidate) / statistics.median(control),
            gpu_snapshot_after=gpu_snapshot(), gpu_processes_after=gpu_process_snapshot(),
            all_outputs_byte_equal=True, report_enabled=False, in_process_oracle=False))
    write_json(args.work / 'summary.json', results)
    print(json.dumps(dict(stage=args.stage, cases=len(results), status='pass')), flush=True)


if __name__ == '__main__':
    main()
