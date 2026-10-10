#!/usr/bin/env python3
"""Development panel, fail-closed controls, and full-input AB/BA timing.

All outputs are append-only. This does not modify any paper acceptance state.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess

from check_gpu_exact_repair_v1 import compare, fasta, run, sha


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=Path('/data/wenyujianData/LongTarget-exact-sim'))
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=('panel', 'faults', 'benchmark'), required=True)
    p.add_argument('--panel-scope', choices=('all', 'long'), default='all')
    p.add_argument('--gpu', default='GPU-d1f5be95-b8a3-3c18-f919-90913038a1a3')
    args = p.parse_args()
    args.binary = args.binary.resolve()
    args.work = args.work.resolve()
    args.work.mkdir(parents=True, exist_ok=False)
    source = args.source_root
    frozen = source / '.paper-artifacts/bioinformatics-submission-readiness-v2'
    inputs = frozen / 'phase3/frozen-inputs'
    w010 = inputs / 'v2p4_w010'
    cpu = source / '.paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86'
    if sha(cpu) != '75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e':
        raise RuntimeError('frozen CPU binary identity changed')
    results = []
    if args.stage == 'panel':
        specs = []
        if args.panel_scope == 'all':
            for label in ('v2p4_w001', 'v2p4_w003', 'v2p4_w007'):
                specs.append((label, inputs / label / 'query.fa', inputs / label / 'target.fa', 100000))
            specs.append(('H19', source / 'H19.fa', source / 'testDNA.fa', 100000))
        long_root = Path('/data/wenyujianData/linjieData/lncrna_sequences/human_GRCh38_GENCODE_v33/gene_exon_union/per_gene')
        for gene in ('ENSG00000229613', 'ENSG00000267107', 'ENSG00000271913'):
            specs.append((gene, long_root / (gene + '.fa'),
                          source / '.tmp/fasim_gasal2_chr22_slice_10m_12m.fa', 20000))
        manifest = []
        # Freeze the entire panel before starting any execution.
        for label, query_source, target_source, length in specs:
            case = args.work / label
            case.mkdir()
            _, query = fasta(query_source)
            header, target = fasta(target_source)
            length = min(length, len(target))
            # Select by input content only: the chr22 slice begins with N-only
            # windows, which execute no DP and cannot validate long queries.
            start = next(i for i in range(0, len(target) - length + 1, length)
                         if sum(c.upper() in 'ACGT' for c in target[i:i + length]) >= length * 0.99)
            (case / 'query.fa').write_text('>' + label + '\n' + query + '\n')
            (case / 'target.fa').write_text(header + '\n' + target[start:start + length] + '\n')
            manifest.append(dict(case=label, query_source=str(query_source),
                                 target_source=str(target_source), query_length=len(query),
                                 target_length=length, target_offset=start,
                                 query_sha256=sha(case / 'query.fa'), target_sha256=sha(case / 'target.fa')))
        write_json(args.work / 'panel.json', dict(purpose='development regression; reused inputs, not fresh acceptance', cases=manifest))
        for spec in manifest:
            case = args.work / spec['case']
            a = run(cpu, case / 'query.fa', case / 'target.fa', case / 'cpu', args.gpu, False, 1200)
            b = run(args.binary, case / 'query.fa', case / 'target.fa', case / 'candidate', args.gpu, True, 1200,
                    {'FASIM_GPU_EXACT_REPAIR_CHECK_SCOREINFO': '1'})
            result = compare(Path(a['output']), Path(b['output']), case)
            result['case'] = spec['case']
            results.append(result)
            if not result['byte_equal']:
                raise RuntimeError('panel output differs: ' + spec['case'])
    elif args.stage == 'faults':
        header, sequence = fasta(w010 / 'target.fa')
        target = args.work / 'target.fa'
        target.write_text(header + '\n' + sequence[:5000] + '\n')
        faults = [
            ('no_gpu', {'CUDA_VISIBLE_DEVICES': ''}),
            ('scoreinfo_capacity', {'FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_MAX_PER_TASK': '1'}),
            ('unsupported_output', {'FASIM_OUTPUT_MODE': 'full'}),
        ]
        for label, env in faults:
            result = run(args.binary, w010 / 'query.fa', target, args.work / label,
                         args.gpu, True, 120, env, expect_failure=True)
            results.append(dict(case=label, returncode=result['returncode'],
                                output_published='output' in result))
    else:
        reference = frozen / 'phase4/formal/v2p4_082_v2p4_w010__repeat00_a/product/diagnostics/native-TFOsorted'
        if sha(reference) != '8e6842d3967d86827ba22f1e0cd3aee17f1340f70f022be9ed537c47ba72d974':
            raise RuntimeError('frozen reference identity changed')
        plan = dict(purpose='development AB/BA; no acceptance promotion',
                    query_sha256=sha(w010 / 'query.fa'), target_sha256=sha(w010 / 'target.fa'),
                    cpu_binary_sha256=sha(cpu), candidate_binary_sha256=sha(args.binary),
                    order=['cpu', 'candidate', 'candidate', 'cpu'],
                    host_affinity=sorted(os.sched_getaffinity(0)),
                    candidate_cpu_continuation=True, consumer_report=False,
                    includes='process start, GPU initialization, all compute, transfer, CPU continuation, sort and output',
                    gpu_snapshot=subprocess.check_output(['nvidia-smi', '--query-gpu=uuid,name,driver_version,utilization.gpu,memory.used', '--format=csv'], text=True))
        write_json(args.work / 'plan.json', plan)
        for number, label in enumerate(plan['order']):
            case = args.work / ('%02d_%s' % (number, label))
            is_candidate = label == 'candidate'
            result = run(args.binary if is_candidate else cpu, w010 / 'query.fa', w010 / 'target.fa',
                         case, args.gpu, is_candidate, 1800, report=False)
            if result['output_sha256'] != sha(reference):
                raise RuntimeError('timed output differs: ' + str(case))
            results.append(dict(case=case.name, backend=label, wall_seconds=result['wall_seconds'],
                                byte_equal=True, output_sha256=result['output_sha256']))
        cpu_wall = [r['wall_seconds'] for r in results if r['backend'] == 'cpu']
        gpu_wall = [r['wall_seconds'] for r in results if r['backend'] == 'candidate']
        write_json(args.work / 'performance.json', dict(
            cpu_wall_seconds=cpu_wall, candidate_wall_seconds=gpu_wall,
            median_speedup=statistics.median(cpu_wall) / statistics.median(gpu_wall),
            limitation='one workload, two repetitions, serial CPU baseline; not an OpenMP or general speed claim'))
    write_json(args.work / 'summary.json', results)


if __name__ == '__main__':
    main()
