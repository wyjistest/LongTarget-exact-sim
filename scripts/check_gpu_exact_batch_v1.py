#!/usr/bin/env python3
"""Append-only exactness and performance checks for cross-task batching.

Uses the frozen repair's development fixtures and CPU outputs. These are not
fresh paper acceptance inputs. Timed runs include process/GPU initialization,
CPU continuation, conversion, sorting, and output.
"""
import argparse
import csv
import itertools
import json
import os
from pathlib import Path
import statistics
import subprocess

from check_gpu_exact_repair_v1 import compare, run, sha


ROOT = Path('/data/wenyujianData/LongTarget-exact-sim')
REPAIR = Path('/data/wenyujianData/linjieData/longtarget_runs/gasal2_exact_repair_20261010_v1')
PREFIX = 'benchmark.fasim_gpu_exact_batch_v1.'
REFERENCE_SHA = '8e6842d3967d86827ba22f1e0cd3aee17f1340f70f022be9ed537c47ba72d974'
REPAIR_SHA = 'a5948c2568e8ac5918d1b21243282fcd5dfe303602a9fda1ad5b576d1f49b255'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def frozen_case(label, directory):
    receipt = json.loads((directory / 'cpu/receipt.json').read_text())
    command = receipt['command']
    query = Path(command[command.index('-f2') + 1])
    target = Path(command[command.index('-f1') + 1])
    reference = Path(receipt['output'])
    if receipt['returncode'] or any(sha(path) != receipt[field] for path, field in (
        (query, 'query_sha256'), (target, 'target_sha256'), (reference, 'output_sha256'))):
        raise RuntimeError('frozen fixture changed: ' + label)
    return dict(label=label, query=str(query), target=str(target), reference=str(reference),
                query_sha256=sha(query), target_sha256=sha(target), reference_sha256=sha(reference),
                consumer_reference=str(directory / 'candidate/consumer.tsv'))


def full_case():
    inputs = ROOT / '.paper-artifacts/bioinformatics-submission-readiness-v2/phase3/frozen-inputs/v2p4_w010'
    reference = ROOT / '.paper-artifacts/bioinformatics-submission-readiness-v2/phase4/formal/v2p4_082_v2p4_w010__repeat00_a/product/diagnostics/native-TFOsorted'
    query, target = inputs / 'query.fa', inputs / 'target.fa'
    if sha(reference) != REFERENCE_SHA or sha(query) != '88305f54d6ca35bb9872de922e55866fa5b5d369e0126e0129873e8cd954e6a7' or sha(target) != 'efd5dac374bead647eaccf90a1ea9bcdd842feca76c377fd434d3e62fa3fff8d':
        raise RuntimeError('frozen full input changed')
    return dict(label='w010', query=str(query), target=str(target), reference=str(reference),
                query_sha256=sha(query), target_sha256=sha(target), reference_sha256=REFERENCE_SHA,
                consumer_reference=str(REPAIR / 'full03/w010/candidate/consumer.tsv'))


def compare_consumers(reference, actual, metrics):
    excluded = {'endpoint_batches'}
    tasks = attempts = batches = 0
    with reference.open() as a, actual.open() as b:
        expected, observed = csv.DictReader(a, delimiter='\t'), csv.DictReader(b, delimiter='\t')
        if expected.fieldnames != observed.fieldnames:
            raise RuntimeError('consumer report schema changed')
        fields = [key for key in expected.fieldnames if key not in excluded and not key.endswith('_seconds')]
        for left, right in itertools.zip_longest(expected, observed):
            if left is None or right is None:
                raise RuntimeError('consumer task count changed')
            differences = [key for key in fields if left[key] != right[key]]
            if differences:
                raise RuntimeError('consumer task %s differs: %s' % (left['task_index'], differences))
            tasks += 1
            attempts += int(right['attempts'])
            batches += int(right['endpoint_batches'])
    for key, value in (('tasks', tasks), ('attempts', attempts), ('endpoint_batches', batches)):
        if int(metrics[PREFIX + key]) != value:
            raise RuntimeError('batch accounting mismatch: ' + key)
    return dict(tasks=tasks, attempts=attempts, endpoint_batches=batches, semantic_fields_equal=True)


def gpu_snapshot():
    return subprocess.check_output(['nvidia-smi',
        '--query-gpu=uuid,name,driver_version,utilization.gpu,memory.used', '--format=csv'], text=True)


def gpu_process_snapshot():
    return subprocess.check_output(['nvidia-smi',
        '--query-compute-apps=gpu_uuid,pid,process_name,used_memory', '--format=csv'], text=True)


def execute(args, spec, label, limit=None, report=False, diagnostic=False, binary=None):
    directory = args.work / label
    env = {'FASIM_GPU_EXACT_BATCH_V1': '1' if limit else '0'}
    if limit:
        env['FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH'] = str(limit)
    if diagnostic:
        env['FASIM_GPU_EXACT_REPAIR_CHECK_SCOREINFO'] = '1'
    receipt = run(binary or args.binary, Path(spec['query']), Path(spec['target']),
                  directory, args.gpu, True, 1800, env, report=report)
    if receipt['output_sha256'] != spec['reference_sha256']:
        compare(Path(spec['reference']), Path(receipt['output']), directory)
        raise RuntimeError('full output differs: ' + label)
    if limit and receipt['metrics'].get(PREFIX + 'active') != '1':
        raise RuntimeError('cross-task mode was not active')
    summary = dict(label=label, batch_limit=limit, wall_seconds=receipt['wall_seconds'],
                   byte_equal=True, output_sha256=receipt['output_sha256'])
    if limit:
        summary['batch'] = {key[len(PREFIX):]: value for key, value in receipt['metrics'].items()
                            if key.startswith(PREFIX)}
    if limit and report:
        summary['consumer_comparison'] = compare_consumers(
            Path(spec['consumer_reference']), directory / 'consumer.tsv', receipt['metrics'])
    write_json(directory / 'comparison.json', summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=('smoke', 'panel', 'full', 'sweep', 'benchmark', 'faults'), required=True)
    p.add_argument('--batch', type=int, default=4096)
    p.add_argument('--gpu', default='GPU-d1f5be95-b8a3-3c18-f919-90913038a1a3')
    args = p.parse_args()
    if not 1 <= args.batch <= 32768:
        p.error('--batch must be between 1 and 32768')
    args.binary = args.binary.resolve()
    args.work = args.work.resolve()
    args.work.mkdir(parents=True, exist_ok=False)
    specs, order = [], []
    if args.stage in ('smoke', 'faults'):
        specs = [frozen_case(name, REPAIR / 'scoreinfo03' / name)
                 for name in ('prefix5000', 'affected_locus')]
        if args.stage == 'smoke':
            order = [(spec, 'case_%s_b%s' % (spec['label'], limit or 'off'), limit)
                     for spec in specs for limit in (None, 7, 1024, 4096, 8192)]
    elif args.stage == 'panel':
        specs = [frozen_case(name, REPAIR / 'panel04' / name)
                 for name in ('H19', 'v2p4_w001', 'v2p4_w003', 'v2p4_w007')]
        specs += [frozen_case(name, REPAIR / 'panel05' / name)
                  for name in ('ENSG00000229613', 'ENSG00000267107', 'ENSG00000271913')]
        order = [(spec, spec['label'], args.batch) for spec in specs]
    else:
        specs = [full_case()]
        if args.stage == 'full':
            order = [(specs[0], 'w010', args.batch)]
        elif args.stage == 'sweep':
            order = [(specs[0], 'batch_%d' % limit, limit) for limit in (1024, 4096, 8192)]
        else:
            order = [(specs[0], '%02d_%s' % (i, label), args.batch if label == 'batched' else None)
                     for i, label in enumerate(('frozen', 'batched', 'batched', 'frozen'))]
    baseline = REPAIR / 'release/fasim_gpu_exact_repair_v1'
    if sha(baseline) != REPAIR_SHA:
        raise RuntimeError('frozen repair binary changed')
    write_json(args.work / 'plan.json', dict(
        stage=args.stage, candidate_binary=str(args.binary), candidate_sha256=sha(args.binary),
        baseline_binary=str(baseline), baseline_sha256=sha(baseline), fixtures=specs,
        order=[dict(label=label, batch_limit=limit) for _, label, limit in order],
        host_affinity=sorted(os.sched_getaffinity(0)), host_load_average=os.getloadavg(),
        gpu_snapshot=gpu_snapshot(), gpu_processes=gpu_process_snapshot(),
        limitation='reused development inputs; no paper acceptance promotion'))
    results = []
    if args.stage == 'faults':
        for label, env in (
            ('missing_repair', {'FASIM_GPU_EXACT_REPAIR_V1': '0'}),
            ('no_gpu', {'CUDA_VISIBLE_DEVICES': ''}),
            ('scoreinfo_capacity', {'FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_MAX_PER_TASK': '1'}),
            ('unsupported_output', {'FASIM_OUTPUT_MODE': 'full'})):
            env['FASIM_GPU_EXACT_BATCH_V1'] = '1'
            receipt = run(args.binary, Path(specs[0]['query']), Path(specs[0]['target']),
                          args.work / label, args.gpu, True, 120, env, expect_failure=True)
            results.append(dict(case=label, returncode=receipt['returncode'], output_published='output' in receipt))
    else:
        for spec, label, limit in order:
            results.append(execute(args, spec, label, limit,
                report=args.stage in ('smoke', 'panel', 'full'),
                diagnostic=args.stage in ('smoke', 'panel'),
                binary=baseline if args.stage == 'benchmark' and limit is None else None))
            write_json(args.work / 'progress.json', results)
    if args.stage == 'benchmark':
        a = [r['wall_seconds'] for r in results if r['batch_limit'] is None]
        b = [r['wall_seconds'] for r in results if r['batch_limit'] is not None]
        write_json(args.work / 'performance.json', dict(
            frozen_wall_seconds=a, batched_wall_seconds=b,
            median_additional_speedup=statistics.median(a) / statistics.median(b),
            wall_reduction_fraction=1 - statistics.median(b) / statistics.median(a),
            gpu_snapshot_after=gpu_snapshot(),
            gpu_processes_after=gpu_process_snapshot(),
            limitation='one workload, two repetitions per backend; not an OpenMP comparison'))
    write_json(args.work / 'summary.json', results)
    print(json.dumps(dict(stage=args.stage, cases=len(results), status='pass')), flush=True)


if __name__ == '__main__':
    main()
