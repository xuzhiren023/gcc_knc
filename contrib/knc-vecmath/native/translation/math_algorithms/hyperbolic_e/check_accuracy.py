"""Fresh six-family MPFR screen/million assay; old measured sources unchanged."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from ProjectHostCompiler import environment,posix


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bits(v,sp):return struct.unpack('<I'if sp else'<Q',struct.pack('<f'if sp else'<d',v))[0]


def corpus(sp,operation,million):
    rng=random.Random(0x485950+(32 if sp else 64)+operation*12345+(0x100000 if million else 0))
    count=1048576 if million else 32768;lanes=16 if sp else 8;width=32 if sp else 64
    sign=1<<(width-1);inf=0x7f800000 if sp else 0x7ff0000000000000
    normal=0x00800000 if sp else 0x0010000000000000;quiet=1<<(22 if sp else 51)
    overflow=89.41598629223294 if sp else 710.4758600739439
    maximum=20 if operation==2 else(95 if sp else 720)
    seen=set();words=[]
    for i in range(count):
        category=i%5
        if category==0:x=rng.randrange(inf)|(sign if rng.randrange(2)else 0)
        elif category==1:x=bits(rng.uniform(-maximum,maximum),sp)
        elif category==2:x=rng.randrange(normal)|(sign if rng.randrange(2)else 0)
        elif category==3:
            center=bits(20. if operation==2 else overflow,sp)
            x=center+rng.randrange(-(1<<(14 if sp else 34)),1<<(14 if sp else 34));x|=sign if rng.randrange(2)else 0
        else:x=bits(rng.uniform(-1,1),sp)
        while x in seen:x=rng.randrange(inf)|(sign if rng.randrange(2)else 0)
        seen.add(x);words.append(x)
    words +=[0,sign,1,sign|1,normal-1,normal,normal+1,inf-1,sign|(inf-1),inf,sign|inf]
    for center in(2.**-27,.1,.2554,.5,1.,20.,overflow,711.):
        c=bits(center,sp)
        for delta in range(-256,257):
            if 0<c+delta<inf:words.extend((c+delta,sign|(c+delta)))
    for _ in range(256):
        payload=rng.randrange(1,quiet);words.extend((inf|payload,sign|inf|quiet|payload))
    while len(words)%lanes:words.append(0)
    allmask=(1<<lanes)-1;rows=[]
    for start in range(0,len(words),lanes):rows.append((allmask,(start//lanes)%3,words[start:start+lanes],
        [rng.getrandbits(width)for _ in range(lanes)]))
    for mask in[0,allmask,allmask//3,2*allmask//3]+[1<<i for i in range(lanes)]+[allmask^(1<<i)for i in range(lanes)]:
        for mode in range(3):
            poison=(inf|1,sign|inf,inf-1,1)
            x=[bits(.25,sp)if mask>>i&1 else poison[(i+mode)%4]for i in range(lanes)]
            rows.append((mask,mode,x,[rng.getrandbits(width)for _ in range(lanes)]))
    return rows,len(seen)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mpfr-million',action='store_true');args=parser.parse_args()
    folder=ROOT/'artifacts/test-state/host-hyperbolic-e'/uuid.uuid4().hex;folder.mkdir(parents=True)
    report=dict(status='Running',hostOnly=True,targetQualified=False,g5Passed=False,commands=[],variants={},
        experiment='Official musl expm1 rational coefficients/split-ln2 with vector DD; strict<=1ULP, specials/flags/masks/aliases')
    started=time.time();tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    def run(argv,expect=0):
        r=subprocess.run(list(map(str,argv)),cwd=ROOT,env=environment(),capture_output=True,text=True,timeout=600)
        report['commands'].append(dict(argv=list(map(str,argv)),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1800:]}')
        return r
    tracked=[HERE/x for x in('hyperbolic_e.c','hyperbolic_e.h','host_assay.c','mpfr_reference.c','check_accuracy.py')]
    try:
        # The kernel has no operation/format compile-time switches. Compile its
        # exact source once per contraction setting; only the pointer driver is
        # specialized for the six exported functions. This preserves both
        # complete builds without repeating the large DD compiler workload.
        kernels={}
        for contraction in('off','fast'):
            flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f',
                '-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans',
                '-ffp-contract='+contraction,'-Wall','-Wextra','-Werror','-Wno-psabi','-Wno-misleading-indentation']
            obj=folder/('hyperbolic-'+contraction+'.o');assembly=folder/('hyperbolic-'+contraction+'.s')
            run([tools/'gcc.exe',*flags,'-c',posix(HERE/'hyperbolic_e.c'),'-o',posix(obj)])
            run([tools/'gcc.exe',*flags,'-S',posix(HERE/'hyperbolic_e.c'),'-o',posix(assembly)])
            text=assembly.read_text();packed=len(re.findall(r'\b(?:add|sub|mul|div)p[sd]\s+[^\n]*%xmm',text))
            if not packed or re.search(r'%[yz]mm|%k[0-7]',text)or re.search(r'\b(?:call|jmp)\s+_?(?:exp|expm1|sinh|cosh|tanh)f?\b',text):raise ValueError('missingvector/fallback')
            kernels[contraction]=(flags,obj,packed)
        for operation,name in enumerate(('sinh','cosh','tanh')):
            for sp in(1,0):
                label=name+('f'if sp else'');lanes=16 if sp else 8;width=32 if sp else 64
                rows,unique=corpus(sp,operation,args.mpfr_million);inp=folder/(label+'-input.bin')
                with inp.open('wb')as stream:
                    stream.write(struct.pack('<8I',0x494c5750,1,lanes,144,len(rows),width,0,0))
                    for i,(mask,mode,x,m)in enumerate(rows):
                        stream.write(struct.pack('<QII'+str(lanes*2)+('I'if sp else'Q'),i,mask,mode,*x,*m))
                oracle=folder/(label+'-mpfr.exe')
                run([tools/'gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
                    '-DPW_SP='+str(sp),'-DPW_OPERATION='+str(operation),posix(HERE/'mpfr_reference.c'),'-lmpfr','-lgmp','-o',posix(oracle)])
                for contraction in('off','fast'):
                    common,obj,packed=kernels[contraction]
                    flags=[*common,'-DPW_SP='+str(sp),'-DPW_OPERATION='+str(operation)]
                    exe=folder/(label+'-'+contraction+'.exe')
                    run([tools/'gcc.exe',*flags,posix(HERE/'host_assay.c'),posix(obj),'-o',posix(exe)])
                    if 'INVALID_MASK_ZERO_FP_UNCHANGED'not in run([exe,'--invalid-mask']).stdout:raise ValueError('invalid mask')
                    raw=folder/(label+'-'+contraction+'.bin');run([exe,posix(inp),posix(raw)])
                    result=json.loads(run([oracle,posix(inp),posix(raw)]).stdout)
                    bad=folder/(label+'-'+contraction+'-wrong.bin');b=bytearray(raw.read_bytes());b[51]^=0x40;bad.write_bytes(b)
                    negative=run([oracle,posix(inp),posix(bad)],expect=None)
                    if negative.returncode not in(6,8):raise ValueError('completed wrong-result negative did not reject')
                    result.update(uniqueFreshFiniteInputs=unique,packedSseLines=packed,wrongResultRejected=True)
                    report['variants'][label+'-'+contraction]=result
        report['status']='MillionInputHostHyperbolicAlgorithmsChecked'if args.mpfr_million else'BoundedHostHyperbolicAlgorithmsChecked'
    except Exception as exc:report.update(status='Stopped',error=f'{type(exc).__name__}: {exc}')
    snapshots=folder/'sources';snapshots.mkdir()
    for path in tracked:shutil.copyfile(path,snapshots/path.name)
    report['sourceSha256']={str(path.relative_to(ROOT)):sha(path)for path in tracked};report['elapsedSeconds']=time.time()-started
    path=folder/'accuracy.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(path=str(path),status=report['status'],variants=report['variants'],error=report.get('error'))))
    return int(report['status']=='Stopped')


if __name__=='__main__':raise SystemExit(main())
