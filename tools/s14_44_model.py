"""Host-only S14-44 experiment; never starts a card job or builds GCC.

Inputs in knc-boinc remain read-only. Generated objects and twin cache metadata
stay in the shared ticket directory. Run through tools/run.py.
"""
import copy
import json
import os
import re
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
OUT = SHARED / 'S14-44'
BOINC = Path('C:/Users/xuzhi/Documents/knc-boinc/.work/S8-09')
TWIN = Path('C:/Users/xuzhi/Documents/knc-twin/scripts')
CC = SHARED / 'gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc.exe'
OBJDUMP = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'
FLAGS = {
    'O2': ['-O2'],
    'O3': ['-O3'],
    'phinix': ['-O3', '-mphinix'],
    'density1': ['-O2', '--param=knc-threads-per-core=1'],
    'density2': ['-O2', '--param=knc-threads-per-core=2'],
    'density4': ['-O2', '--param=knc-threads-per-core=4'],
    'unroll': ['-O2', '-funroll-loops'],
    'nosched': ['-O2', '-fno-schedule-insns', '-fno-schedule-insns2'],
    'frame': ['-O2', '-fno-omit-frame-pointer'],
    'inline': ['-O2', '-finline-limit=1000'],
}


def command(args):
    args = [str(a) for a in args]
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, errors='replace')
    if p.returncode:
        print(p.stdout[-4500:])
        raise RuntimeError('command exit %d: %s' % (p.returncode, ' '.join(args)))
    return p.stdout


def twin(action, kernel, dest):
    args = [sys.executable, TWIN / 'knc_twin.py', action, kernel,
            '--profile', 'card-7120-measured', '--out', dest, '--force']
    if action == 'simulate':
        args += ['--max-seconds', '30', '--no-issue-log']
    p = subprocess.run([str(a) for a in args], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    data = json.loads((dest / 'result.json').read_text())
    pred = data.get('prediction') or {}
    print(dest.name, 'exit', p.returncode, 'status', data['status'],
          'cycles', pred.get('predicted_cycles'), 'bound', pred.get('lower_bound_cycles'),
          'unsupported', data.get('unsupported', []), flush=True)
    return data


def phase0():
    OUT.mkdir(exist_ok=True, parents=True)
    upstream = BOINC / 'third_party/milkywayathome_client_196'
    options = (BOINC / 'build/card/.build-options').read_text().splitlines()[0].split()
    cpp = ['-I' + str((BOINC / 'mk' / x[2:]).resolve()) if x.startswith('-I') else x
           for x in options]
    # These options preserve the application's established math/alias contract.
    common = ['-march=knc', '-ffp-contract=off', '-fno-fast-math',
              '-fno-math-errno', '-fno-strict-aliasing', '-std=gnu99', '-fopenmp']
    inputs = {
        'tree': upstream / 'nbody/src/nbody_tree.c',
        'subindex': BOINC / 'probes/s8_subindex.c',
        'df': BOINC / 'probes/s8_df_reuse.c',
        'walk': BOINC / 'probes/walk-prefetch.c',
    }
    for name, flags in FLAGS.items():
        for label, src in inputs.items():
            obj = OUT / (label + '-' + name + '.o')
            command([CC, *common, *flags, *(cpp if label == 'tree' else []),
                     '-save-temps=obj', '-c', src, '-o', obj])
            # Preprocessed third-party source is redundant; retain only .s/.o.
            obj.with_suffix('.i').unlink(missing_ok=True)
        print('compiled', name, ' '.join(common + flags), flush=True)

    memory = []
    calls = []
    expected = []
    for case in range(9):
        p = [1. if case & (4 >> j) else -1. for j in range(3)]
        if case == 8:
            p = [0., 0., 0.]
        addr = 0x20001000 + case * 256
        memory += [dict(addr=hex(addr), hex=struct.pack('<3d', *p).hex()),
                   dict(addr=hex(addr + 64), hex=struct.pack('<3d', 0., 0., 0.).hex())]
        calls.append(dict(registers=dict(rdi=hex(addr + 128), rsi=hex(addr),
                                         rdx=hex(addr + 64))))
        expected.append(dict(addr=hex(addr + 128),
                             hex=struct.pack('<i', case if case < 8 else 7).hex()))
    init = dict(init=dict(memory=memory), expected=dict(memory=expected),
                numerical_policy=dict(rounding='rn', ftz=False, daz=False,
                                      x87_control_word='0x027f'),
                scenario=dict(memory=dict(type='line_tracking', cold_level='l1'),
                              branch=dict(type='all_predicted')),
                unit_of_work=dict(count=9, description='eight octants and equality'))
    initpath = OUT / 'subindex-input.json'
    initpath.write_text(json.dumps(init, indent=2))
    for name in FLAGS:
        path = OUT / ('subindex-' + name + '.json')
        command([sys.executable, TWIN / 'from_binary.py',
                 OUT / ('subindex-' + name + '.o'), '--function', 's8_subindex',
                 '--objdump', OBJDUMP, '--init', initpath, '--out', path,
                 '--report', OUT / ('subindex-' + name + '-adapter.json')])
        kernel = json.loads(path.read_text())
        kernel['streams'][0]['calls_table'] = calls
        path.write_text(json.dumps(kernel, indent=2))
        twin('simulate', path, OUT / ('subindex-' + name + '-simulate'))
        twin('bounds', path, OUT / ('subindex-' + name + '-bounds'))


def adapt(obj, function, name, init):
    initpath = OUT / (name + '-input.json')
    initpath.write_text(json.dumps(init, indent=2))
    path = OUT / (name + '.json')
    command([sys.executable, TWIN / 'from_binary.py', obj, '--function', function,
             '--objdump', OBJDUMP, '--init', initpath, '--out', path,
             '--report', OUT / (name + '-adapter.json')])
    return path


def pair_runs(path, name, two=True, private_scratch=False):
    original = json.loads(path.read_text())
    for contexts in ([1, 2] if two else [1]):
        kernel = copy.deepcopy(original)
        if contexts == 2:
            stream = copy.deepcopy(kernel['streams'][0])
            stream['context'] = 1
            if private_scratch:
                # Each worker gets its own scratch line. Sharing a written
                # line with another worker's loads is unsupported by the twin.
                stream.setdefault('init', {}).setdefault('registers', {})['rdi'] = '0x27000000'
                kernel['init']['memory'] += [
                    dict(addr='0x27000000', f64=[1.]),
                    dict(addr='0x27000040', hex='02000000')]
            kernel['streams'].append(stream)
            kernel['unit_of_work']['count'] *= 2
            # Read-only inputs are shared; output memory is the same value.
            # The core model permits this; it is not a coherence experiment.
            if 'registers' in kernel.get('expected', {}):
                kernel['expected']['registers']['1'] = copy.deepcopy(
                    kernel['expected']['registers']['0'])
        kpath = OUT / (name + '-t%d.json' % contexts)
        kpath.write_text(json.dumps(kernel, indent=2))
        for action in ('simulate', 'bounds'):
            twin(action, kpath, OUT / (name + '-t%d-' % contexts + action))


def regions():
    obj = OUT / 'lane0.o'
    command([CC, '-march=knc', '-x', 'assembler', '-c',
             ROOT / 'tools/s14_44_lane0.asm', '-o', obj])
    command([sys.executable, ROOT / 'tools/knc_lint', obj])
    init = json.loads((OUT / 'subindex-input.json').read_text())
    path = adapt(obj, 's14_subindex', 'subindex-lane', init)
    kernel = json.loads(path.read_text())
    kernel['streams'][0]['calls_table'] = json.loads(
        (OUT / 'subindex-O2.json').read_text())['streams'][0]['calls_table']
    path.write_text(json.dumps(kernel, indent=2))
    # Match the already completed phase-0 scenario, including its cold effects.
    pair_runs(path, 'subindex-lane', two=False)

    # Exact compiler loop, extracted from the retained -O2 assembly (S12-08).
    source = (SHARED / 'S12-08/ludcmp.s').read_text()
    block = source[source.index('\n.L31:') + 1:]
    block = block[:re.search(r'\tjg\s+\.L31', block).end()]
    block = '\n'.join(line.split('#')[0] for line in block.splitlines())
    base = OUT / 'ludcmp-x87.s'
    base.write_text('.text\n.globl s14_lud_base\n.type s14_lud_base,@function\n'
                    's14_lud_base:\n' + block + '\nret\n'
                    '.size s14_lud_base,.-s14_lud_base\n')
    command([CC, '-march=knc', '-c', base, '-o', base.with_suffix('.o')])
    regs = dict(r10='0x21000000', r15='0x22000000', rcx=0, r8=8,
                x87=[16.], zmm0=dict(f64_broadcast=16.))
    mem = [dict(addr=hex(0x21000000 + 4096*i), f64=[1.]) for i in range(8)]
    mem.append(dict(addr='0x22000000', f64=[0.5]*8))
    common = dict(init=dict(registers=regs, memory=mem),
                  numerical_policy=dict(rounding='rn', ftz=False, daz=False,
                                        x87_control_word='0x027f'),
                  scenario=dict(memory=dict(type='fixed_level', level='l1'),
                                branch=dict(type='all_predicted')),
                  unit_of_work=dict(count=8, description='eight ordered ludcmp products'))
    for mode in ('x87', 'lane'):
        init = copy.deepcopy(common)
        expected = dict(st0=12., x87_depth=1) if mode == 'x87' else dict(
            zmm0=dict(f64=[12.] + [16.]*7))
        init['expected'] = dict(registers={'0': expected})
        path = adapt(base.with_suffix('.o') if mode == 'x87' else obj,
                     's14_lud_base' if mode == 'x87' else 's14_ludcmp',
                     'ludcmp-' + mode, init)
        pair_runs(path, 'ludcmp-' + mode)

    mixobj = OUT / 'mix-x87.o'
    command([CC, '-O2', '-march=knc', '-ffp-contract=off', '-save-temps=obj',
             '-c', ROOT / 'tools/s14_44_mix.c', '-o', mixobj])
    mixobj.with_suffix('.i').unlink(missing_ok=True)
    data = [(i*17 + 3) % 256 for i in range(32)]
    hash_value = 0
    for d in data:
        hash_value = (((hash_value << 5) | (hash_value >> 27)) ^ d) & 0xffffffff
    init = copy.deepcopy(common)
    init['init'] = dict(registers=dict(rdi='0x23000000', rsi='0x24000000',
                                     rdx='0x25000000', rcx=32),
                        memory=[dict(addr='0x23000000', hex=bytes(data).hex()),
                                dict(addr='0x24000000', f64=[i/256 for i in range(256)])])
    init['expected'] = dict(registers={'0': dict(eax=hash_value)},
                            memory=[dict(addr='0x25000000', f64=[sum(data)/256])])
    init['unit_of_work'] = dict(count=32, description='32 ordered hash and score updates')
    for mode in ('x87', 'lane'):
        path = adapt(mixobj if mode == 'x87' else obj,
                     's14_mix' if mode == 'x87' else 's14_mix_lane', 'mix-' + mode, init)
        pair_runs(path, 'mix-' + mode)


def operations():
    """Composite probes and register chains; no isolated-latency claim."""
    asm = ['.text']
    forms = {
        'x87_add': 'fadd %st(1), %st',
        'x87_sub': 'fsub %st(1), %st',
        'x87_mul': 'fmul %st(1), %st',
        'x87_div': 'fdiv %st(1), %st',
        'x87_sqrt': 'fsqrt',
        'lane_add': 'vaddpd %zmm7, %zmm0, %zmm0{%k1}',
        'lane_sub': 'vsubpd %zmm7, %zmm0, %zmm0{%k1}',
        'lane_mul': 'vmulpd %zmm7, %zmm0, %zmm0{%k1}',
        'lane_fma': 'vfmadd213pd %zmm7, %zmm7, %zmm0{%k1}',
        'x87_compare': 'fcom %st(1)\nfnstsw %ax\ntestb $5, %ah\njne 1f\n1:',
        'lane_compare': 'vcmppd $2, %zmm7, %zmm0, %k2{%k1}\nkmov %k2, %eax\ntestl %eax, %eax\nje 1f\n1:',
        'x87_loadstore': 'fldl (%rdi)\nfstpl (%rdi)',
        'lane_loadstore': 'vbroadcastsd (%rdi), %zmm0\nvpackstorelpd %zmm0, (%rdi){%k1}',
        'x87_to_lane': 'fstl (%rdi)\nvbroadcastsd (%rdi), %zmm0',
        'lane_to_x87': 'vpackstorelpd %zmm0, (%rdi){%k1}\nfldl (%rdi)\nfstp %st(0)',
        'x87_int_roundtrip': 'fildl 64(%rdi)\nfistpl 64(%rdi)',
        'lane_to_int': 'vcvtfxpntpd2dq $0, %zmm7, %zmm0{%k1}',
    }
    for name, body in forms.items():
        asm += ['.globl ' + name, '.type ' + name + ',@function', name + ':',
                '\n'.join([body]*32), 'ret', '.size ' + name + ',.-' + name]
    src = OUT / 'operations.s'
    src.write_text('\n'.join(asm) + '\n.section .note.GNU-stack,"",@progbits\n')
    obj = src.with_suffix('.o')
    command([CC, '-march=knc', '-c', src, '-o', obj])
    command([sys.executable, ROOT / 'tools/knc_lint', obj, OUT / 'mix-x87.o'])
    init = dict(init=dict(registers=dict(rdi='0x26000000', k1=1,
                          x87=[2., 1.], zmm0=dict(f64_broadcast=1.),
                          zmm7=dict(f64_broadcast=2.)),
                          memory=[dict(addr='0x26000000', f64=[1.]),
                                  dict(addr='0x26000040', hex='02000000')]),
                numerical_policy=dict(rounding='rn', ftz=False, daz=False,
                                      x87_control_word='0x027f'),
                scenario=dict(memory=dict(type='fixed_level', level='l1'),
                              branch=dict(type='all_predicted')),
                unit_of_work=dict(count=32, description='32 repetitions of named operation sequence'))
    for name in forms:
        path = adapt(obj, name, 'op-' + name, init)
        # These timing inputs have no independent expected-value oracle. The
        # interpreter traces them, but this is not a numerical correctness test.
        pair_runs(path, 'op-' + name, private_scratch=True)


if __name__ == '__main__':
    os.environ['PATH'] = str(SHARED / 'toolchain/cross/bin') + os.pathsep + str(
        SHARED / 'toolchain/cygwin/bin') + os.pathsep + os.environ['PATH']
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    {'phase0': phase0, 'regions': regions, 'operations': operations}[
        sys.argv[1] if len(sys.argv) > 1 else 'phase0']()
