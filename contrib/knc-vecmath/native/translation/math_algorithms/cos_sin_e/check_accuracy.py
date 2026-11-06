"""Bounded independent MPFR assay for the new full-domain trig sources only."""
import hashlib
import json
from pathlib import Path
import math
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
def bits(x,sp):return struct.unpack('<I' if sp else '<Q',struct.pack('<f' if sp else '<d',x))[0]
def corpus(sp,million):
    rng=random.Random(0x54524947+(32 if sp else 64)+(0x100000 if million else 0));lanes=16 if sp else 8
    sign=1<<(31 if sp else 63);inf=0x7f800000 if sp else 0x7ff0000000000000;normal=0x00800000 if sp else 0x0010000000000000;quiet=0x00400000 if sp else 0x0008000000000000
    count=1048576 if million else 32768;words=[];seen=set()
    for i in range(count):
        category=i&3
        if category==0:x=rng.randrange(1,inf)
        elif category==1:x=rng.randrange(1,normal)
        elif category==2:
            value=rng.randrange(-1048576,1048577)*math.pi/2
            x=bits(value,sp)&(sign-1);x=max(1,min(inf-1,x+rng.randrange(-16,17)))
        else:x=bits(rng.uniform(-8.,8.),sp)&(sign-1)
        x|=sign if rng.getrandbits(1) else 0
        while x in seen:x=rng.randrange(1,inf)|(sign if rng.getrandbits(1) else 0)
        seen.add(x);words.append(x)
    directed=[0,sign,1,sign|1,normal-1,normal,normal+1,inf-2,inf-1,inf,sign|inf]
    for value in [2.**-27,math.pi/4,math.pi/2,math.pi,3*math.pi/2,2*math.pi,2.**20*math.pi/2]:
        b=bits(value,sp)
        for delta in range(-4,5):directed.extend([b+delta,sign|b+delta])
    for e in range(-125 if sp else -1020,128 if sp else 1024,1 if not million else 3):
        value=math.ldexp(math.pi/2,e)
        if sp and value>3.4028234663852886e38:continue
        b=bits(value,sp)
        for delta in [-1,0,1]:directed.extend([max(1,min(inf-1,b+delta)),sign|max(1,min(inf-1,b+delta))])
    for _ in range(128):
        payload=rng.randrange(1,quiet);directed.extend([inf|payload,sign|inf|quiet|payload])
    words+=directed
    while len(words)%lanes:words.append(0)
    rows=[];allmask=(1<<lanes)-1
    for start in range(0,len(words),lanes):rows.append((allmask,(start//lanes)%3,words[start:start+lanes],[rng.getrandbits(32 if sp else 64) for _ in range(lanes)]))
    if not million:
        poison=[inf|1,inf,sign|inf,inf|quiet|123]
        for mask in [0,allmask,allmask//3,2*(allmask//3)]+[1<<i for i in range(lanes)]+[allmask^(1<<i) for i in range(lanes)]:
            for mode in range(3):
                rows.append((mask,mode,[(sign if i&1 else 0) if mask&(1<<i) else poison[(i+mode)%4] for i in range(lanes)],[rng.getrandbits(32 if sp else 64) for _ in range(lanes)]))
    categories={'small':0,'medium':0,'large':0,'subnormal':0,'negative':0,'zero':0,'nonfinite':0}
    for _,_,x,_ in rows:
        for b in x:
            mag=b&(sign-1);categories['negative']+=bool(b&sign)
            if mag>=inf:categories['nonfinite']+=1;continue
            value=struct.unpack('<f' if sp else '<d',struct.pack('<I' if sp else '<Q',mag))[0]
            categories['subnormal']+=0<mag<normal;categories['zero']+=mag==0
            categories['small' if value<=math.pi/4 else 'medium' if value<2**20*math.pi/2 else 'large']+=1
    return rows,len(seen),categories

def main():
    million=sys.argv[1:]==['--mpfr-million']
    if sys.argv[1:] and not million:raise SystemExit('only --mpfr-million supported')
    folder=ROOT/'artifacts/test-state/host-cos-sin-e'/uuid.uuid4().hex;folder.mkdir(parents=True)
    record={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'profile':'strict baselineSSE2; noAVX/FMA; nearest-even/masked/FTZ-DAZ-off','commands':[],'variants':{}}
    started=time.time();tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    tracked=[HERE/x for x in ['cos_sin_e.c','cos_sin_e.h','libm.h','reducer.c','host_assay.c','mpfr_reference.c','check_accuracy.py','README.md']]+sorted((HERE/'upstream').glob('*'))
    snapshot=folder/'sources';snapshot.mkdir()
    before={str(p.relative_to(HERE)):sha(p) for p in tracked}
    for p in tracked:
        dest=snapshot/p.relative_to(HERE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    record['sourceSha256']=before
    try:
        def run(argv,expect=0):
            r=subprocess.run(list(map(str,argv)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=300)
            record['commands'].append({'argv':list(map(str,argv)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1600:]}')
            return r
        run([tools/'gcc.exe','--version'])
        for name,sp,cosine in [('sinf',1,0),('cosf',1,1),('sin',0,0),('cos',0,1)]:
            lanes=16 if sp else 8;precision=32 if sp else 64
            rows,unique,categories=corpus(sp,million);inp=folder/(name+'-input.bin')
            with inp.open('wb') as stream:
                stream.write(struct.pack('<8I',0x494c5750,1,lanes,144,len(rows),precision,0,0))
                for i,(mask,mode,x,m) in enumerate(rows):stream.write(struct.pack('<QII'+str(lanes*2)+('I' if sp else 'Q'),i,mask,mode,*x,*m))
            oracle=folder/(name+'-mpfr.exe');run([tools/'gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-DPW_SP='+str(sp),'-DPW_COS='+str(cosine),posix(HERE/'mpfr_reference.c'),'-lmpfr','-lgmp','-o',posix(oracle)])
            previous=None
            for contraction in ('off','fast'):
                flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-error=attributes','-Wno-psabi','-Wno-misleading-indentation','-DPW_SP='+str(sp),'-DPW_COS='+str(cosine),'-ffp-contract='+contraction,'-I'+posix(HERE)]
                exe=folder/(name+'-'+contraction+'.exe');run([tools/'gcc.exe',*flags,posix(HERE/'host_assay.c'),posix(HERE/'cos_sin_e.c'),posix(HERE/'reducer.c'),'-o',posix(exe)])
                if 'INVALID_MASK_ZERO_FP_UNCHANGED' not in run([exe,'--invalid-mask']).stdout:raise ValueError('invalid mask control')
                raw=folder/(name+'-'+contraction+'.bin');run([exe,posix(inp),posix(raw)])
                if previous is not None and previous[0].read_bytes()==raw.read_bytes():
                    result=dict(previous[1]);result['mpfrBoundByCompleteRawEqualityWith']=name+'-off'
                else:result=json.loads(run([oracle,posix(inp),posix(raw)]).stdout)
                assembly=folder/(name+'-'+contraction+'.s');run([tools/'gcc.exe',*flags,'-S',posix(HERE/'cos_sin_e.c'),'-o',posix(assembly)])
                text=assembly.read_text();packed=len(re.findall(r'\b(?:add|sub|mul|div)p[sd]\s+[^\n]*%xmm',text))
                imports=run([tools/'nm.exe','-u',posix(exe)]).stdout
                if not packed or re.search(r'%[yz]mm|%k[0-7]',text) or re.search(r'\b(?:sin|cos|sinf|cosf|sincos|sincosf|floor|scalbn)\b',imports):raise ValueError('wrong arithmetic profile/scalar import')
                bad=folder/(name+'-'+contraction+'-wrong.bin');b=bytearray(raw.read_bytes());b[32+16+(3 if sp else 7)]^=0x40;bad.write_bytes(b)
                neg=run([oracle,posix(inp),posix(bad)],expect=None)
                if neg.returncode not in (6,8):raise ValueError('complete negative failed for nonnumerical reason')
                result.update({'uniqueRandomFiniteInputs':unique,'inputCategories':categories,'packedSseArithmeticLines':packed,'binarySha256':sha(exe),'inputSha256':sha(inp),'rawSha256':sha(raw),'assemblySha256':sha(assembly),'completedWrongResultRejected':True})
                record['variants'][name+'-'+contraction]=result
                if contraction=='off':previous=(raw,result)
        if before!={str(p.relative_to(HERE)):sha(p) for p in tracked}:raise ValueError('source changed during assay')
        record['status']='MillionInputHostTrigAlgorithmsChecked' if million else 'BoundedHostTrigAlgorithmsChecked'
    except Exception as e:record['status']='Stopped';record['error']=f'{type(e).__name__}: {e}'
    record['elapsedSeconds']=time.time()-started;(folder/'accuracy.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':record['status'],'artifact':str(folder/'accuracy.json'),'variants':record['variants'],'error':record.get('error')},indent=2))
    return int(record['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
