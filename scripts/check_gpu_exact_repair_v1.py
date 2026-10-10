#!/usr/bin/env python3
"""Append-only development regression against the frozen CPU authority."""
import argparse
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def fasta(path):
    lines = path.read_text().splitlines()
    return lines[0], ''.join(lines[1:])


def run(binary, query, target, directory, gpu, candidate, timeout,
        extra_env=None, report=True, expect_failure=False):
    directory.mkdir(parents=True, exist_ok=False)
    out = directory / 'out'
    out.mkdir()
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('FASIM_', 'CUDA_', 'OMP_', 'MALLOC_'))}
    env.update(CUDA_VISIBLE_DEVICES=gpu, FASIM_OUTPUT_MODE='tfosorted',
               FASIM_VERBOSE='0', MALLOC_ARENA_MAX='16')
    if candidate:
        env['FASIM_GPU_EXACT_REPAIR_V1'] = '1'
        if report:
            env['FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_REPORT'] = str(directory / 'consumer.tsv')
    env.update(extra_env or {})
    command = [str(binary), '-f1', str(target), '-f2', str(query), '-r', '0', '-O', str(out)]
    start = time.monotonic()
    with (directory / 'stdout.log').open('w') as stdout, (directory / 'stderr.log').open('w') as stderr:
        completed = subprocess.run(command, env=env, stdout=stdout, stderr=stderr, timeout=timeout)
    receipt = dict(command=command, binary_sha256=sha(binary), returncode=completed.returncode,
                   wall_seconds=time.monotonic() - start,
                   query_sha256=sha(query), target_sha256=sha(target),
                   environment={k: v for k, v in env.items()
                                if k.startswith(('FASIM_', 'CUDA_', 'MALLOC_'))})
    outputs = list(out.glob('*-TFOsorted'))
    if len(outputs) == 1:
        receipt['output'] = str(outputs[0])
        receipt['output_sha256'] = sha(outputs[0])
        with outputs[0].open() as f:
            rows = list(csv.reader(f, delimiter='\t'))
        receipt['data_rows'] = max(0, len(rows) - 1)
        receipt['bad_rows'] = sum(len(row) != 19 for row in rows)
    if candidate and (directory / 'consumer.tsv').is_file():
        with (directory / 'consumer.tsv').open() as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        fields = ('attempts', 'gpu_scored_attempts', 'cpu_oracle_attempts',
                  'cpu_reference_align_attempts', 'control_selected_attempts',
                  'cpu_continuation_calls', 'cpu_continuation_failures', 'cpu_align_attempts',
                  'cpu_continuation_reselection_groups', 'cpu_continuation_extra_calls')
        receipt['consumer'] = {key: sum(int(row[key]) for row in rows) for key in fields}
        receipt['consumer']['tasks'] = len(rows)
        receipt['consumer']['errors'] = sum(row['ok'] != '1' or row['error'] != 'none' for row in rows)
    metrics = {}
    for line in (directory / 'stderr.log').read_text().splitlines():
        if line.startswith('benchmark.') and '=' in line:
            key, value = line.split('=', 1)
            metrics[key] = value
    receipt['metrics'] = metrics
    failures = []
    if expect_failure:
        if completed.returncode == 0:
            failures.append('negative control unexpectedly succeeded')
        if outputs:
            failures.append('negative control published a TFOsorted result')
    elif candidate and completed.returncode == 0:
        prefix = 'benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_'
        for field in ('fallback_batches', 'overflow_batches', 'gpu_minscore_fallbacks',
                      'gpu_minscore_score_mismatches', 'gpu_minscore_min_score_mismatches',
                      'scoreinfo_mismatches', 'candidate_missing', 'candidate_extra'):
            if metrics.get(prefix + field) != '0':
                failures.append(field + ' is not zero')
        for field in ('active', 'gpu_minscore_active', 'gpu_minscore_hot'):
            if metrics.get(prefix + field) != '1':
                failures.append(field + ' is not active')
        for field in ('error', 'gpu_minscore_error'):
            if metrics.get(prefix + field) != 'none':
                failures.append(field + ' is not none')
        if (extra_env or {}).get('FASIM_GPU_EXACT_REPAIR_CHECK_SCOREINFO') == '1':
            if metrics.get(prefix + 'realpath_trust') != '0':
                failures.append('scoreInfo diagnostic skipped the CPU comparison')
            if metrics.get(prefix + 'gpu_scoreinfo_groups') != metrics.get(prefix + 'cpu_scoreinfo_groups'):
                failures.append('scoreInfo group counts differ')
        if report:
            counts = receipt.get('consumer', {})
            if not counts.get('tasks'):
                failures.append('consumer report missing or empty')
            else:
                for field in ('cpu_oracle_attempts', 'cpu_reference_align_attempts',
                              'cpu_continuation_failures', 'errors'):
                    if counts[field] != 0:
                        failures.append(field + ' is not zero')
                if counts['attempts'] != counts['gpu_scored_attempts']:
                    failures.append('not all attempts were GPU scored')
                if counts['cpu_continuation_calls'] != (counts['control_selected_attempts'] +
                                                       counts['cpu_continuation_extra_calls']):
                    failures.append('continuation accounting mismatch')
    receipt['contract_failures'] = failures
    (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items()
                      if k in ('returncode', 'wall_seconds', 'data_rows', 'output_sha256', 'consumer')},
                     ensure_ascii=False), flush=True)
    if failures or (not expect_failure and
                    (completed.returncode != 0 or len(outputs) != 1 or receipt['bad_rows'])):
        raise RuntimeError('execution failed: ' + str(directory))
    return receipt


def compare(reference, candidate, directory):
    with reference.open() as f:
        expected = list(csv.reader(f, delimiter='\t'))
    with candidate.open() as f:
        actual = list(csv.reader(f, delimiter='\t'))
    a = collections.Counter(map(tuple, expected[1:]))
    b = collections.Counter(map(tuple, actual[1:]))
    result = dict(byte_equal=sha(reference) == sha(candidate),
                  header_equal=expected[0] == actual[0],
                  missing_rows=sum((a - b).values()), extra_rows=sum((b - a).values()),
                  reference_sha256=sha(reference), candidate_sha256=sha(candidate))
    for name, rows in [('missing.tsv', a - b), ('extra.tsv', b - a)]:
        with (directory / name).open('w') as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerow(expected[0])
            writer.writerows(rows.elements())
    (directory / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, default=Path('/data/wenyujianData/LongTarget-exact-sim'))
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=('smoke', 'full'), default='smoke')
    p.add_argument('--gpu', default='GPU-d1f5be95-b8a3-3c18-f919-90913038a1a3')
    p.add_argument('--timeout', type=int, default=1200)
    p.add_argument('--check-scoreinfo', action='store_true')
    args = p.parse_args()
    args.binary = args.binary.resolve()
    args.work = args.work.resolve()
    args.work.mkdir(parents=True, exist_ok=False)
    frozen = args.source_root / '.paper-artifacts/bioinformatics-submission-readiness-v2'
    inputs = frozen / 'phase3/frozen-inputs/v2p4_w010'
    cpu = args.source_root / '.paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86'
    query = inputs / 'query.fa'
    target = inputs / 'target.fa'
    assert sha(query) == '88305f54d6ca35bb9872de922e55866fa5b5d369e0126e0129873e8cd954e6a7'
    assert sha(target) == 'efd5dac374bead647eaccf90a1ea9bcdd842feca76c377fd434d3e62fa3fff8d'
    assert sha(cpu) == '75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e'
    cases = []
    if args.stage == 'smoke':
        header, sequence = fasta(target)
        for label, start, length in [('prefix5000', 0, 5000), ('affected_locus', 16493400, 10000)]:
            case = args.work / label
            case.mkdir()
            view = case / 'target.fa'
            view.write_text(header + '\n' + sequence[start:start + length] + '\n')
            authority = run(cpu, query, view, case / 'cpu', args.gpu, False, args.timeout)
            cases.append((case, query, view, Path(authority['output'])))
    else:
        reference = frozen / 'phase4/formal/v2p4_082_v2p4_w010__repeat00_a/product/diagnostics/native-TFOsorted'
        assert sha(reference) == '8e6842d3967d86827ba22f1e0cd3aee17f1340f70f022be9ed537c47ba72d974'
        case = args.work / 'w010'
        case.mkdir()
        cases.append((case, query, target, reference))
    results = []
    for case, query, target, reference in cases:
        candidate = run(args.binary, query, target, case / 'candidate', args.gpu, True, args.timeout,
                        {'FASIM_GPU_EXACT_REPAIR_CHECK_SCOREINFO': '1'} if args.check_scoreinfo else {})
        result = compare(reference, Path(candidate['output']), case)
        result['case'] = case.name
        result['consumer'] = candidate.get('consumer', {})
        results.append(result)
    (args.work / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    if not all(item['byte_equal'] for item in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
