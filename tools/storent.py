"""S8-13 streaming stores: T1 scans and the card publish test's build.

    python tools/run.py --name S8-13-t1 -- python tools/check.py t1 --compiler gcc16 --storent
    python tools/run.py --name S8-13-t2 -- python tools/check.py t2 --compiler gcc16 --storent

t1 runs tests/t1/knc-storent.c.  t2 compiles tests/t2/knc-storent-publish.c
at -O2, requires its stream_fill to take the no-read store path (vmovnrngoaps
and the lock addl fence, so the card run exercises what it claims) and its
--control writer to stream without a fence, links the pthread program and
lints it.  The binary is staged for the lead under
.work/_shared/S8-13/knc-storent-publish.mic; the engineer never runs it.
"""
import re
import sys

NGO_STORE = re.compile(r'\bvmovnrngoaps\s+%zmm\d+,\s*[^\n]*\(%r')
FENCE = re.compile(r'\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\)')


def t1(runner):
    runner.t1_sources([runner.source_dir / 'knc-storent.c'])


def t2(runner):
    from check import function_body
    out = runner.tc.parent / 'S8-13'
    out.mkdir(parents=True, exist_ok=True)
    source = runner.root / 'tests/t2/knc-storent-publish.c'
    asm = out / 'knc-storent-publish.s'
    elf = out / 'knc-storent-publish.mic'
    flags = ['-O2', '-pthread', '--sysroot=' + str(runner.sysroot)]
    failures = []
    compiled = runner.command(runner.cc, *runner.cc_flags, *flags, '-S', source, '-o', asm,
                              check=False)
    if compiled.returncode:
        failures.append('compile: ' + compiled.stdout[-1600:])
    else:
        text = asm.read_text()
        for name, fenced in (('stream_fill', True), ('stream_fill_control', False)):
            body = function_body(text, name)
            if body is None:
                failures.append(name + ': missing function boundary')
                continue
            if not NGO_STORE.search(body):
                failures.append(name + ': no vmovnrngoaps store')
            if bool(FENCE.search(body)) != fenced:
                failures.append(name + (': no lock addl $0,(%rsp) fence' if fenced
                                        else ': has a fence'))
    runner.result('t2 storent publish test takes the NGO path', failures)
    linked = runner.command(runner.cc, *runner.cc_flags, *flags, source, '-o', elf, check=False)
    failures = ['link: ' + linked.stdout[-1600:]] if linked.returncode else []
    if not failures:
        lint = runner.command(sys.executable, runner.root / 'tools/knc_lint', elf, check=False)
        if lint.returncode:
            failures.append('lint: ' + lint.stdout[-1600:])
    runner.result('t2 storent publish test links and lints', failures)
    runner.say('Staged, not run: ' + str(elf))
