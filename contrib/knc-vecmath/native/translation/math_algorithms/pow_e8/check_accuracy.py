"""New DP family, same strict host/independent MPFR interval method as powf.
Not a card runner or translated library qualification.
"""
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from ProjectHostCompiler import environment,posix
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bits(x):return struct.unpack('<Q',struct.pack('<d',x))[0]

def corpus(million=False):
    rng=random.Random(0x504f5744384d5046 ^ (0x1d99f05a if million else 0))
    pairs=[]
    xs=[1,2,3,0x000fffffffffffff,0x0010000000000000,0x0010000000000001,
        0x3fe69554ffffffff,0x3fe6955500000000,0x3fefffffffffffff,0x3ff0000000000000,
        0x3ff0000000000001,0x3fffffffffffffff,0x4000000000000000,0x4000000000000001,
        0x7feffffffffffffe,0x7fefffffffffffff]
    ys=[bits(x) for x in [-1075.,-1074.5,-1074.,-1024.,-32.,-3.,-2.,-1.5,-1.,-.5,-2**-66,0.,2**-66,.5,1.,1.5,2.,3.,32.,1023.,1024.,1074.,1075.]]
    if not million:
        for x in xs:
            pairs.extend((x,y) for y in ys)
            pairs.extend((x|0x8000000000000000,bits(float(y))) for y in range(-9,10))
    count=1048576 if million else 32768
    for i in range(count):
        category=i&3
        if category==0:
            x=rng.randrange(1,0x7ff0000000000000);y=bits(rng.uniform(-1,1))
        elif category==1:
            x=rng.randrange(1,0x7ff0000000000000);y=bits((1 if rng.randrange(2) else -1)*rng.uniform(.25,.75))
        elif category==2:
            x=0x3ff0000000000000+rng.randrange(-8192,8193)
            y=bits(rng.uniform(-2**52,2**52))
        else:
            x=rng.randrange(1,0x7ff0000000000000)|0x8000000000000000;y=bits(float(rng.randrange(-2,3)))
        pairs.append((x,y))
    for _ in range(262144 if million else 4096):
        x=rng.randrange(1,0x7ff0000000000000)|(rng.randrange(2)<<63)
        y=rng.randrange(0,0x7ff0000000000000)|(rng.randrange(2)<<63)
        pairs.append((x,y))
    # Very-near-one / huge exponent cancellation; y parity close to2^53.
    for delta in range(-32,33):
        for exponent in (50,52,53,60,62,63,65):
            x=0x3ff0000000000000+delta;y=bits(float(2**exponent))
            pairs.extend([(x,y),(x,y|0x8000000000000000),(x|0x8000000000000000,y)])
    specials=[0,0x8000000000000000,1,0x8000000000000001,0x0010000000000000,0x8010000000000000,
              0x3fe0000000000000,0xbfe0000000000000,0x3ff0000000000000,0xbff0000000000000,
              0x4000000000000000,0xc000000000000000,0x7fefffffffffffff,0xffefffffffffffff,
              0x7ff0000000000000,0xfff0000000000000,0x7ff8123456789abc,0xfff8123456789abc,
              0x7ff0123456789abc,0xfff0123456789abc]
    pairs.extend((x,y) for x in specials for y in specials)
    while len(pairs)%8:pairs.append((bits(1.),0))
    rows=[]
    for start in range(0,len(pairs),8):
        block=pairs[start:start+8];rows.append((255,(start//8)%4,[p[0] for p in block],[p[1] for p in block],[rng.getrandbits(64) for _ in block]))
    if not million:
        poison=[(0x7ff0000000000001,bits(1.)),(bits(-1.),bits(.5)),(0,bits(-1.)),(0x7fefffffffffffff,0x7fefffffffffffff),(1,0x7fefffffffffffff)]
        for mask in [0,255,0x55,0xaa]+[1<<i for i in range(8)]+[255^(1<<i) for i in range(8)]:
            for mode in range(4):
                x=[];y=[]
                for lane in range(8):
                    p=(bits(1.),bits(3.)) if mask&(1<<lane) else poison[(lane+mode)%len(poison)];x.append(p[0]);y.append(p[1])
                rows.append((mask,mode,x,y,[rng.getrandbits(64) for _ in range(8)]))
    return rows

def main():
    million=sys.argv[1:]==['--mpfr-million']
    if sys.argv[1:] and not million:raise SystemExit('only --mpfr-million supported')
    folder=ROOT/'artifacts/test-state/host-pow-e8'/uuid.uuid4().hex;folder.mkdir(parents=True)
    record={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'profile':'baselineSSE2; noAVX/FMA; nearest-even/masked/FTZ-DAZ-off','commands':[],'variants':{}}
    started=time.time();tools=ROOT/'.tools/knc-bootstrap/cygwin/bin';config=ROOT/'native/upstream/arm-optimized-routines-v26.01-dp/math';data=config/'exp_data.c'
    sources=[HERE/'host_assay.c',HERE/'pow_e8.c',HERE/'upstream/pow_log_data.c',data]
    tracked=[*sources,HERE/'pow_e8.h',HERE/'mpfr_reference.c',Path(__file__),config/'math_config.h']
    try:
        def run(argv,expect=0,timeout=300):
            result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=timeout)
            record['commands'].append({'argv':list(map(str,argv)),'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
            if expect is not None and result.returncode!=expect:raise ValueError(f'exit{result.returncode}: {result.stderr[-1600:]}')
            return result
        rows=corpus(million);inp=folder/'input.bin'
        with inp.open('wb') as f:
            f.write(struct.pack('<8I',0x49574450,1,8,208,len(rows),0,0,0))
            for i,(mask,mode,x,y,m) in enumerate(rows):f.write(struct.pack('<QII24Q',i,mask,mode,*x,*y,*m))
        oracle=folder/'mpfr-oracle.exe';run([tools/'gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',posix(HERE/'mpfr_reference.c'),'-lmpfr','-lgmp','-o',posix(oracle)])
        for contraction in ('off','fast'):
            flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-error=attributes','-Wno-psabi','-Wno-misleading-indentation','-DHAVE_FAST_FMA=0','-ffp-contract='+contraction,'-I'+posix(HERE),'-I'+posix(config)]
            exe=folder/('pow-'+contraction+'.exe');run([tools/'gcc.exe',*flags,*map(posix,sources),'-o',posix(exe)])
            cap=json.loads(run([exe,'--capabilities']).stdout)
            if cap['mxcsr']!=0x1f80 or cap['rounding']:raise ValueError('unknown host profile')
            if not million and 'INVALID_MASK_ZERO_FP_UNCHANGED' not in run([exe,'--invalid-mask']).stdout:raise ValueError('invalid mask control')
            raw=folder/('pow-'+contraction+'.bin');run([exe,posix(inp),posix(raw)])
            result=json.loads(run([oracle,posix(inp),posix(raw)]).stdout)
            assembly=folder/('pow-'+contraction+'.s');run([tools/'gcc.exe',*flags,'-S',posix(HERE/'pow_e8.c'),'-o',posix(assembly)])
            text=assembly.read_text();packed=len(re.findall(r'\b(?:add|sub|mul|div)pd\s+[^\n]*%xmm',text))
            if not packed or re.search(r'%[yz]mm|%k[0-7]',text) or re.search(r'\b(?:call|jmp)\s+_?(?:pow|log|exp)\b',text):raise ValueError('unexpected arithmetic/delegation profile')
            bad=folder/('wrong-'+contraction+'.bin');mutant=bytearray(raw.read_bytes());mutant[32+16+7]^=0x40;bad.write_bytes(mutant)
            neg=run([oracle,posix(inp),posix(bad)],expect=None)
            if neg.returncode not in (6,8):raise ValueError('complete numerical negative failed for wrong reason')
            result.update({'capabilities':cap,'packedSseArithmeticLines':packed,'binarySha256':sha(exe),'rawSha256':sha(raw),'assemblySha256':sha(assembly),'completedWrongResultRejected':True})
            record['variants'][contraction]=result
        record['status']='MillionInputHostPowAlgorithmChecked' if million else 'BoundedHostPowAlgorithmChecked'
    except Exception as error:record['status']='Stopped';record['error']=f'{type(error).__name__}: {error}'
    snapshot=folder/'sources';snapshot.mkdir()
    for p in tracked:shutil.copyfile(p,snapshot/('upstream-'+p.name if p.parent.name=='upstream' else p.name))
    record['sourceSha256']={str(p.relative_to(ROOT)):sha(p) for p in tracked};record['elapsedSeconds']=time.time()-started
    (folder/'accuracy.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':record['status'],'artifact':str(folder/'accuracy.json'),'variants':record['variants'],'error':record.get('error')},indent=2))
    return int(record['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
