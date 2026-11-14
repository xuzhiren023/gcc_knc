"""S12-21 phase-one builds and a lead-only, bounded card batch.

The installed prefix and existing development sources are read-only inputs.
No GCC build, held-out workload, card launch, or performance claim occurs here.
"""
import argparse
from collections import Counter
import difflib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tarfile

DEVELOPMENT = ('PB-gemm', 'PB-atax', 'PB-cholesky', 'PB-ludcmp',
               'PB-jacobi-2d', 'PB-heat-3d', 'STREAM', 'NPB-CG', 'NPB-EP',
               'NPB-MG', 'NPB-IS', 'HPCG', 'zlib', 'SQLite')
FLAGS = {'default': ['-O2', '-march=knc'],
         'density1': ['-O2', '-march=knc', '--param=knc-threads-per-core=1']}


def build_plan():
    return [dict(program=p, label=label, compiler='gcc-knc', variant='serial', flags=list(flags))
            for p in DEVELOPMENT for label, flags in FLAGS.items()]


def card_plan(differences):
    if set(differences) != set(DEVELOPMENT):
        raise ValueError('require exactly the fourteen development programs')
    if any(type(x) is not int or x < 0 for x in differences.values()):
        raise ValueError('code difference counts must be nonnegative integers')
    selected = sorted(DEVELOPMENT, key=lambda p: (-differences[p], p))[:4]
    pairs = []
    for run in range(3):
        for program in selected:
            for label in (('default', 'density1') if run % 2 == 0 else ('density1', 'default')):
                pairs.append(dict(program=program, run=run, label=label,
                                  compiler='gcc-knc', flags=list(FLAGS[label]), threads=1,
                                  profile='full', benchmark=True, variant='serial', timeout=60))
    return dict(selected=selected, pairs=pairs,
                imul=dict(threads=1, profile='full', benchmark=True, timeout=120,
                          cases=[(bits, form, dependency) for bits in (32, 64)
                                 for form in ('register', 'memory')
                                 for dependency in ('dependent', 'independent')]))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf8', newline='\n') as stream:
        stream.write(text)


def save_json(path, value):
    write(path, json.dumps(value, indent=2, allow_nan=False) + '\n')


def imul_assembly():
    lines = ['.text']
    wide = ['r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'rax', 'rcx']
    narrow = ['r8d', 'r9d', 'r10d', 'r11d', 'r12d', 'r13d', 'eax', 'ecx']
    for bits in (32, 64):
        for form in ('register', 'memory'):
            for dep in ('dependent', 'independent'):
                name = 'imul_%d_%s_%s' % (bits, form, dep)
                lines += ['.p2align 6', '.globl '+name, '.type '+name+',@function', name+':',
                          'pushq %r12', 'pushq %r13', 'movl $3,%edx']
                lines += ['movl $1,%'+r for r in narrow]
                lines += ['.p2align 6', '.L'+name+':']
                regs = wide if bits == 64 else narrow
                operand = ('%rdx' if bits == 64 else '%edx') if form == 'register' else '(%rsi)'
                for i in range(64):
                    lines.append('imul%s %s,%%%s' % ('q' if bits == 64 else 'l', operand,
                                                   regs[i % 8 if dep == 'independent' else 0]))
                lines += ['decq %rdi', 'jnz .L'+name]
                if dep == 'dependent':
                    lines += ['movq %r8,%rax']
                else:
                    lines += ['addq %'+r+',%rax' for r in wide if r != 'rax']
                lines += ['popq %r13', 'popq %r12', 'ret', '.size %s,.-%s' % (name, name)]
    return '\n'.join(lines + ['.section .note.GNU-stack,"",@progbits', ''])


def runtime_files(binary, compiler, directory, log):
    """Copy needed non-system DSOs without producing provenance records."""
    import corpus
    readelf = corpus.SHARED / 'toolchain/cross/bin/k1om-mpss-linux-readelf'
    system = {'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1', 'ld-linux-k1om.so.2'}
    queue, seen, files = [binary], set(), []
    while queue:
        current = queue.pop()
        dynamic = subprocess.check_output([str(readelf), '-d', str(current)], text=True)
        for name in re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic):
            if name in system or name in seen:
                continue
            seen.add(name)
            path = Path(subprocess.check_output([str(corpus.compiler_path(compiler)),
                                               '-print-file-name='+name], text=True).strip())
            if not path.is_file():
                raise ValueError('missing runtime '+name)
            target = directory / name
            shutil.copyfile(path, target)
            files.append(target)
            queue.append(target)
    return files


def register(name):
    aliases = {'eax': 'rax', 'ax': 'rax', 'al': 'rax', 'ah': 'rax',
               'ebx': 'rbx', 'bx': 'rbx', 'bl': 'rbx', 'bh': 'rbx',
               'ecx': 'rcx', 'cx': 'rcx', 'cl': 'rcx', 'ch': 'rcx',
               'edx': 'rdx', 'dx': 'rdx', 'dl': 'rdx', 'dh': 'rdx',
               'edi': 'rdi', 'di': 'rdi', 'dil': 'rdi',
               'esi': 'rsi', 'si': 'rsi', 'sil': 'rsi', 'ebp': 'rbp', 'esp': 'rsp'}
    return aliases.get(name, re.sub(r'^(r\d+)[dwb]$', r'\1', name))


def loop_chains(instructions, labels):
    """Static register loop-carried recurrences, not a dynamic critical path.

    Count a register when it is read before its first write and is also written
    inside a backward-branch interval. Exclude flags, memory and implicit x87
    stack state; nested intervals are reported separately, not deduplicated.
    """
    loops = []
    for end, line in enumerate(instructions):
        op, _, operands = line.partition(' ')
        if not op.startswith('j') or operands not in labels or labels[operands] > end:
            continue
        start = labels[operands]
        written, incoming, multiplies = set(), set(), set()
        for insn in instructions[start:end+1]:
            opcode, _, args = insn.partition(' ')
            names = [register(x) for x in re.findall(r'%([a-z][a-z0-9]*)', args)]
            dest = re.search(r'(?:^|,)\s*%([a-z][a-z0-9]*)$', args)
            target = register(dest[1]) if dest else None
            no_write = opcode.startswith(('j', 'cmp', 'test', 'push', 'call', 'ret', 'prefetch'))
            reads = set(names)
            if target and not no_write:
                # Remove only the final destination occurrence for pure writes
                # and three-operand arithmetic, retaining explicit source reads.
                if opcode.startswith(('mov', 'lea', 'set', 'pop')) or (args.count(',') == 2 and '(' not in args):
                    reads = set(names[:-1])
                if opcode.startswith('xor') and len(names) == 2 and names[0] == names[1]:
                    reads = set()
            incoming.update(reads - written)
            if target and not no_write:
                written.add(target)
                if opcode.startswith('imul'):
                    multiplies.add(target)
        carriers = (incoming & written) - {'rsp', 'rbp', 'rip'}
        loops.append(dict(start=start, end=end, registers=sorted(carriers),
                          vector_registers=sorted(r for r in carriers if r.startswith('zmm')),
                          imul_registers=sorted(carriers & multiplies)))
    return loops


def assembly_records(folder):
    records = {}
    for source in sorted(folder.glob('*.s')):
        name, lines, labels, local = None, [], {}, {}
        def normalize(text):
            def label(match):
                key = match[0]
                if key not in local:
                    local[key] = '.Lnorm%d' % len(local)
                return local[key]
            return re.sub(r'\.L[A-Za-z_]*\d+\b', label, text)
        for raw in source.read_text(errors='replace').splitlines():
            line = raw.split('#', 1)[0].strip()
            match = re.match(r'\.type\s+([^,]+),\s*@function', line)
            if match:
                name, lines, labels, local = match[1], [], {}, {}
            elif name and line.startswith('.size'):
                records[source.name + ':' + name] = dict(instructions=lines, loops=loop_chains(lines, labels),
                    imul=[dict(position=i, instruction=s) for i, s in enumerate(lines) if s.startswith('imul')])
                name = None
            elif name and line.endswith(':'):
                labels[normalize(line[:-1])] = len(lines)
            elif name and line and not line.startswith('.'):
                lines.append(normalize(re.sub(r'\s+', ' ', line)))
    if not records:
        raise ValueError('no function assembly found in '+str(folder))
    return records


def census(out):
    differences, summary = {}, {}
    for program in DEVELOPMENT:
        variants = {label: assembly_records(out / label / program) for label in FLAGS}
        metrics = {}
        for label, functions in variants.items():
            loops = [loop for f in functions.values() for loop in f['loops']]
            metrics[label] = dict(instructions=sum(len(f['instructions']) for f in functions.values()),
                                 imul=sum(len(f['imul']) for f in functions.values()),
                                 loops=len(loops), chains=sum(len(x['registers']) for x in loops),
                                 vector_chains=sum(len(x['vector_registers']) for x in loops),
                                 imul_chains=sum(len(x['imul_registers']) for x in loops))
        changes = []
        for name in sorted(set(variants['default']) | set(variants['density1'])):
            a = variants['default'].get(name, {}).get('instructions', [])
            b = variants['density1'].get(name, {}).get('instructions', [])
            edits = [dict(kind=kind, default=[i, j], density1=[k, l])
                     for kind, i, j, k, l in difflib.SequenceMatcher(None, a, b).get_opcodes()
                     if kind != 'equal']
            if edits:
                changes.append(dict(function=name, edits=edits,
                                    changed=sum(max(x['default'][1]-x['default'][0],
                                                    x['density1'][1]-x['density1'][0]) for x in edits)))
        differences[program] = sum(x['changed'] for x in changes)
        summary[program] = dict(changed=differences[program], **metrics)
        save_json(out / 'code' / (program+'.json'), dict(variants=variants, changes=changes))
    save_json(out / 'code-summary.json', summary)
    return card_plan(differences)


def package(out, plan):
    import corpus
    # One reservation for IMUL and all adjacent pairs. Serial launcher pins each
    # workload to the same first granted CPU; shell retains full granted affinity.
    lines = ['#!/bin/sh', 'set -eu', 'cd -- "$(dirname -- "$0")"',
             'tar -xzf payload.tar.gz', 'chmod +x launch imul.mic',
             'echo S12_21_IMUL_BEGIN', 'timeout 120 ./imul.mic', 'echo S12_21_IMUL_END']
    runtimes = {}
    with tarfile.open(out / 'payload.tar.gz', 'w:gz') as archive:
        for name in ('launch', 'imul.mic', 'input.bin', 'input.sql', 'hpcg.dat'):
            archive.add(out / name, arcname=name)
        for label in FLAGS:
            for program in plan['selected']:
                folder = out / label / program
                archive.add(folder / 'workload', arcname=label+'/'+program+'/workload')
                # All variants resolve DSOs from the same installed prefix.
                # Keep one archive copy of each, without copying source trees.
                for p in folder.glob('*.so*'):
                    runtimes.setdefault(p.name, p)
                if program == 'zlib':
                    peer = out / ('density1' if label == 'default' else 'default') / program
                    with tarfile.open(folder / 'peer.tar', 'w') as peer_archive:
                        for p in [peer / 'workload', *peer.glob('*.so*')]:
                            peer_archive.add(p, arcname=p.name)
                    archive.add(folder / 'peer.tar', arcname=label+'/'+program+'/peer.tar')
        for name, path in sorted(runtimes.items()):
            archive.add(path, arcname='runtime/'+name)
    (out / 'payload.tar').unlink(missing_ok=True)
    if (out / 'payload.tar.gz').stat().st_size > 64 * 1024 * 1024:
        raise ValueError('payload exceeds the card runner default staging limit')
    for index, row in enumerate(plan['pairs']):
        folder = row['label']+'/'+row['program']
        lines += ['echo S12_21_PAIR_BEGIN '+str(index), '(', 'cd '+folder,
                  'chmod +x workload', 'ln -sf ../../input.bin input.bin',
                  'ln -sf ../../input.sql input.sql', 'ln -sf ../../hpcg.dat hpcg.dat',
                  'for lib in ../../runtime/*; do [ ! -f "$lib" ] || ln -sf "$lib" "${lib##*/}"; done',
                  'timeout %d ../../launch serial %s' % (row['timeout'], row['program']),
                  ')', 'echo S12_21_PAIR_END '+str(index)]
    lines += ['echo "RESULT S12-21 PASS"', '']
    write(out / 'batch.sh', '\n'.join(lines))
    subprocess.run(['sh', '-n', str(out / 'batch.sh')], check=True)
    write(out / 'files.txt', corpus.windows_path(out / 'payload.tar.gz')+'\n')
    save_json(out / 'card-plan.json', plan)
    write(out / 'README.txt',
          'Lead only; one exclusive full-profile reservation, no smaller inputs or profiles.\n'
          'Serial workload timeout 60 s each; IMUL 120 s; total work deadlines 1560 s; outer 1740 s.\n'
          'Timeout/failure stops the batch and is not a result or a reason to shorten fixed inputs.\n'
          'IMUL pins one granted CPU; register and hot-L1 memory operands, 64 unrolled operations,\n'
          'one dependent stream versus eight independent streams, three samples, checked answers.\n'
          'TSC ticks/op include loop overhead; tsc_hz is measured against MONOTONIC_RAW.\n'
          'Do not equate TSC ticks to core clocks without reviewing clock/power conditions.\n'
          'The card runner records reservation/environment. No native result exists at staging.\n'
          'LEAD (Windows project root, preserve stdout/stderr in .work/_shared/S12-21/native.log):\n'
          'python tools/card_run --benchmark --profile full --threads 240 --timeout 1740 '
          '--file-list .work/_shared/S12-21/files.txt .work/_shared/S12-21/batch.sh\n'
          'COLLECT: python tools/s12_21_stage.py collect .work/_shared/S12-21/native.log\n')


def stage(only):
    import corpus
    out = corpus.SHARED / 'S12-21'
    source = corpus.SHARED / 'corpus-build/sources'
    out.mkdir(exist_ok=True)
    with (out / 'support.log').open('w' if not only else 'a') as log:
        if not only:
            corpus.execute(['gcc', source / 'NPB3.4.2/NPB3.4-OMP/sys/setparams.c',
                            '-o', out / 'setparams'], out, log)
            corpus.execute([corpus.compiler_path(corpus.KNC), '-O2', '-march=knc',
                            corpus.SUPPORT / 'launch.c', *corpus.link_paths(), '-lrt', '-pthread',
                            '-o', out / 'launch'], out, log)
            corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', out / 'launch'], out, log)
            write(out / 'imul.S', imul_assembly())
            corpus.execute([corpus.compiler_path(corpus.KNC), '-O2', '-march=knc',
                            '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                            corpus.ROOT / 'tools/s12_21_imul.c', out / 'imul.S',
                            *corpus.link_paths(), '-lrt', '-o', out / 'imul.mic'], out, log)
            corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', out / 'imul.mic'], out, log)
            with (out / 'imul.asm').open('w') as disassembly:
                subprocess.run([str(corpus.SHARED / 'toolchain/cross/bin/k1om-mpss-linux-objdump'),
                                '-d', str(out / 'imul.mic')], stdout=disassembly, check=True)
            # Same deterministic input generation as the frozen corpus driver.
            state, data = 11, bytearray()
            text = b'GCC KNC corpus fixed input\n'
            for i in range(8 * 1024 * 1024):
                state = (1664525 * state + 1013904223) & 0xffffffff
                data.append((state >> 24) if i % 4096 < 1024 else text[i % len(text)])
            (out / 'input.bin').write_bytes(data)
            shutil.copyfile(corpus.SUPPORT / 'input.sql', out / 'input.sql')
            write(out / 'hpcg.dat', 'HPCG fixed work\nS11-28: one benchmark CG set\n104 104 104\n0\n')
    allowed = {r['label']+'/'+r['program'] for r in build_plan()}
    if set(only) - allowed:
        raise ValueError('invalid selective build')
    for row in build_plan():
        key = row['label']+'/'+row['program']
        if only and key not in only:
            continue
        folder = out / key
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'build.log').open('w') as log:
            corpus.build_program(row['program'], corpus.KNC,
                                 row['flags'] + ['-save-temps=obj'], source, folder,
                                 log, out / 'setparams', variant='serial', runtime_stager=runtime_files)
        # Keep assembly for census, not preprocessed input or intermediate objects.
        for pattern in ('*.i', '*.ii', '*.o', '*.mod'):
            for path in folder.glob(pattern):
                path.unlink()
        print('BUILT/LINTED '+key, flush=True)
    plan = census(out)
    package(out, plan)
    print('STAGED 28 serial builds, eight IMUL forms; top four: '+', '.join(plan['selected']))
    print('No card execution; lead command in '+str(out / 'README.txt'))


def collect(path):
    import corpus
    out = corpus.SHARED / 'S12-21'
    plan = json.loads((out / 'card-plan.json').read_text())
    text = path.read_text(errors='replace')
    if text.count('RESULT S12-21 PASS') != 1 or text.count('RESULT IMUL PASS') != 1:
        raise ValueError('batch incomplete/failed; no paired conclusion')
    samples = re.findall(r'^IMUL_SAMPLE (32|64) (register|memory) (dependent|independent) repeat=(\d+) .*ticks_per_op=([\d.]+)', text, re.M)
    expected = Counter((str(bits), form, dep, str(run)) for bits, form, dep in plan['imul']['cases'] for run in range(3))
    if Counter(tuple(s[:4]) for s in samples) != expected or any(not math.isfinite(float(s[4])) or float(s[4]) <= 0 for s in samples):
        raise ValueError('missing/invalid IMUL samples')
    blocks = re.findall(r'^S12_21_PAIR_BEGIN (\d+)\r?\n(.*?)^S12_21_PAIR_END \1\r?$', text, re.M | re.S)
    if [int(i) for i, _ in blocks] != list(range(len(plan['pairs']))):
        raise ValueError('missing, duplicate, reordered or incomplete pair')
    results = [corpus.output_result(dict(job, input=corpus.INPUTS[job['program']]), body, '', 0)
               for job, (_, body) in zip(plan['pairs'], blocks)]
    for first, second in zip(results[::2], results[1::2]):
        if first['check'] != 'pass' or second['check'] != 'pass':
            raise ValueError('native correctness failure: '+first['program'])
        if first['affinity'] != second['affinity']:
            raise ValueError('pair affinity changed')
        if 'arrays' in first and not corpus.arrays_match(first['arrays'], second['arrays']):
            raise ValueError('A/B output mismatch: '+first['program'])
        if 'hpcg_work' in first and first['hpcg_work'] != second['hpcg_work']:
            raise ValueError('HPCG work changed')
    answer = {}
    for program in plan['selected']:
        ratios = []
        for run in range(3):
            pair = {r['label']: r['time_seconds'] for r in results if r['program'] == program and r['run'] == run}
            ratios.append(pair['default']/pair['density1'])
        answer[program] = dict(default_over_density1=ratios, median=statistics.median(ratios))
    save_json(out / 'native-analysis.json', dict(programs=answer, imul=samples,
              qualification='Review exclusive reservation, clocks, sibling activity and variability before phase 2.'))
    print(json.dumps(answer, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    build = sub.add_parser('stage')
    build.add_argument('--only', nargs='+', default=[], help='resume failed/unbuilt label/program rows only')
    sub.add_parser('package', help='refresh only the lead package after a packaging change')
    result = sub.add_parser('collect')
    result.add_argument('log', type=Path)
    args = parser.parse_args()
    if args.action == 'collect':
        collect(args.log)
    elif os.name == 'nt':
        root = Path(__file__).resolve().parents[1]
        tc = root.parent / '_shared/toolchain'
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(tc / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'), '-u', __file__], env=env, text=True).strip()
        return subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    elif args.action == 'package':
        import corpus
        out = corpus.SHARED / 'S12-21'
        package(out, json.loads((out / 'card-plan.json').read_text()))
        print('PACKAGED', (out / 'payload.tar.gz').stat().st_size, 'bytes; shell syntax PASS; no rebuild or card run')
    else:
        stage(args.only)
    return 0


if __name__ == '__main__':
    sys.exit(main())
