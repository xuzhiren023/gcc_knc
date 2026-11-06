"""Fresh log10f/log10 accuracy extension of the established MPFR host assay."""
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
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from ProjectHostCompiler import environment,posix
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bits(v,sp):return struct.unpack('<I' if sp else '<Q',struct.pack('<f' if sp else '<d',v))[0]

def corpus(sp,million):
    rng=random.Random(0x4c4f473130+(32 if sp else 64)+(0x1011000 if million else 0));lanes=16 if sp else 8
    one=0x3f800000 if sp else 0x3ff0000000000000;sign=1<<(31 if sp else 63);inf=0x7f800000 if sp else 0x7ff0000000000000;normal=0x00800000 if sp else 0x0010000000000000
    count=1048576 if million else 32768;words=[];seen=set()
    for i in range(count):
        category=i&3
        if category==0:x=rng.randrange(1,inf)
        elif category==1:x=one+rng.randrange(-(1<<(19 if sp else 40)),1<<(19 if sp else 40))
        elif category==2:x=rng.randrange(1,normal)
        else:
            exponent=rng.randrange(-44 if sp else -323,39 if sp else 309)
            x=max(1,min(inf-1,bits(10.**exponent,sp)+rng.randrange(-(1<<(10 if sp else 30)),1<<(10 if sp else 30))))
        while x in seen:x=rng.randrange(1,inf)
        seen.add(x);words.append(x)
    words += [0,sign,1,sign|1,normal-1,normal,normal+1,one-2,one-1,one,one+1,one+2,inf-2,inf-1,inf,sign|inf]
    quiet=0x00400000 if sp else 0x0008000000000000
    for _ in range(512):
        payload=rng.randrange(1,quiet)
        words.extend([inf|payload,sign|inf|quiet|payload,sign|rng.randrange(1,inf)])
    while len(words)%lanes:words.append(one)
    rows=[];allmask=(1<<lanes)-1
    for start in range(0,len(words),lanes):rows.append((allmask,(start//lanes)%3,words[start:start+lanes],[rng.getrandbits(32 if sp else 64) for _ in range(lanes)]))
    if not million:
        poison=[inf|1,sign|one,0,sign|inf]
        for mask in [0,allmask,allmask//3,2*(allmask//3)]+[1<<i for i in range(lanes)]+[allmask^(1<<i) for i in range(lanes)]:
            for mode in range(3):
                x=[one if mask&(1<<i) else poison[(i+mode)%4] for i in range(lanes)]
                rows.append((mask,mode,x,[rng.getrandbits(32 if sp else 64) for _ in range(lanes)]))
    return rows,len(seen)

def main():
    million=sys.argv[1:]==['--mpfr-million']
    if sys.argv[1:] and not million:raise SystemExit('only --mpfr-million supported')
    folder=ROOT/'artifacts/test-state/host-log10-e'/uuid.uuid4().hex;folder.mkdir(parents=True)
    record={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'profile':'strict baselineSSE2; noAVX/FMA; nearest-even/masked/FTZ-DAZ-off','commands':[],'variants':{}}
    started=time.time();tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    tracked=[HERE/x for x in ['e_log10f.c','e_log10.c','log10_e.h','host_assay.c','mpfr_reference.c','check_accuracy.py']]
    try:
        def run(argv,expect=0):
            r=subprocess.run(list(map(str,argv)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=300)
            record['commands'].append({'argv':list(map(str,argv)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1600:]}')
            return r
        for name,sp in [('log10f',1),('log10',0)]:
            lanes=16 if sp else 8;precision=32 if sp else 64;kernel=HERE/('e_'+name+'.c')
            rows,unique=corpus(sp,million);inp=folder/(name+'-input.bin')
            with inp.open('wb') as stream:
                stream.write(struct.pack('<8I',0x494c5750,1,lanes,144,len(rows),precision,0,0))
                for i,(mask,mode,x,m) in enumerate(rows):stream.write(struct.pack('<QII'+str(lanes*2)+('I' if sp else 'Q'),i,mask,mode,*x,*m))
            oracle=folder/(name+'-mpfr.exe');run([tools/'gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-DPW_SP='+str(sp),posix(HERE/'mpfr_reference.c'),'-lmpfr','-lgmp','-o',posix(oracle)])
            for contraction in ('off','fast'):
                flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-error=attributes','-Wno-psabi','-Wno-misleading-indentation','-DHAVE_FAST_FMA=0','-DPW_SP='+str(sp),'-ffp-contract='+contraction,'-I'+posix(HERE)]
                exe=folder/(name+'-'+contraction+'.exe');run([tools/'gcc.exe',*flags,posix(HERE/'host_assay.c'),posix(kernel),'-o',posix(exe)])
                if not million and 'INVALID_MASK_ZERO_FP_UNCHANGED' not in run([exe,'--invalid-mask']).stdout:raise ValueError('invalid mask control')
                raw=folder/(name+'-'+contraction+'.bin');run([exe,posix(inp),posix(raw)])
                result=json.loads(run([oracle,posix(inp),posix(raw)]).stdout)
                assembly=folder/(name+'-'+contraction+'.s');run([tools/'gcc.exe',*flags,'-S',posix(kernel),'-o',posix(assembly)])
                text=assembly.read_text();packed=len(re.findall(r'\b(?:add|sub|mul|div)p[sd]\s+[^\n]*%xmm',text))
                if not packed or re.search(r'%[yz]mm|%k[0-7]',text) or re.search(r'\b(?:call|jmp)\s+_?(?:log10f?|logf?)\b',text):raise ValueError('wrong arithmetic profile/fallback')
                bad=folder/(name+'-'+contraction+'-wrong.bin');b=bytearray(raw.read_bytes());b[32+16+(3 if sp else 7)]^=0x40;bad.write_bytes(b)
                neg=run([oracle,posix(inp),posix(bad)],expect=None)
                if neg.returncode not in (6,8):raise ValueError('complete negative failed for nonnumerical reason')
                result.update({'uniquePositiveFiniteInputs':unique,'packedSseArithmeticLines':packed,'binarySha256':sha(exe),'inputSha256':sha(inp),'rawSha256':sha(raw),'assemblySha256':sha(assembly),'completedWrongResultRejected':True})
                record['variants'][name+'-'+contraction]=result
        record['status']='MillionInputHostLog10AlgorithmsChecked' if million else 'BoundedHostLog10AlgorithmsChecked'
    except Exception as e:record['status']='Stopped';record['error']=f'{type(e).__name__}: {e}'
    snapshot=folder/'sources';snapshot.mkdir()
    for p in tracked:shutil.copyfile(p,snapshot/p.name)
    record['sourceSha256']={str(p.relative_to(ROOT)):sha(p) for p in tracked};record['elapsedSeconds']=time.time()-started
    (folder/'accuracy.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':record['status'],'artifact':str(folder/'accuracy.json'),'variants':record['variants'],'error':record.get('error')},indent=2))
    return int(record['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
