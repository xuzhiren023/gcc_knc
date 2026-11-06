"""Fresh bounded atan/atan2 MPFR assay; no consumed math suite is run."""
import hashlib,json,math,random,re,shutil,struct,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from ProjectHostCompiler import environment,posix
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bits(x,sp):return struct.unpack('<I' if sp else '<Q',struct.pack('<f' if sp else '<d',x))[0]
def corpus(sp,binary,million):
    rng=random.Random(0x4154414e+(32 if sp else 64)+binary*111+(0x100000 if million else 0));lanes=16 if sp else 8;sign=1<<(31 if sp else 63);inf=0x7f800000 if sp else 0x7ff0000000000000;normal=0x00800000 if sp else 0x0010000000000000;quiet=0x00400000 if sp else 0x0008000000000000;one=0x3f800000 if sp else 0x3ff0000000000000;shift=23 if sp else 52
    def raw():return rng.randrange(1,inf)|(sign if rng.getrandbits(1) else 0)
    count=1048576 if million else 32768;pairs=[];seen=set()
    for i in range(count):
        cat=i&3
        if cat==0:a,b=raw(),raw()
        elif cat==1:a,b=rng.randrange(1,normal)|(sign if rng.getrandbits(1) else 0),raw()
        elif cat==2:
            b=raw();mag=b&(sign-1);a=max(1,min(inf-1,mag+rng.randrange(-16,17)))|(sign if rng.getrandbits(1) else 0)
            if not binary:a=bits(rng.choice([.4375,.6875,1.1875,2.4375])+rng.uniform(-.001,.001),sp)|(sign if rng.getrandbits(1) else 0)
        else:
            b=raw();exponent=(b&(sign-1))>>shift;target=max(1,min((inf>>shift)-1,exponent+rng.choice([-66,-65,-64,-63,-60,-1,0,1,60,63,64,65,66])));a=(target<<shift)|rng.getrandbits(shift)|(sign if rng.getrandbits(1) else 0)
        key=(a,b) if binary else (a,one)
        while key in seen:key=(raw(),raw() if binary else one)
        seen.add(key);pairs.append(key)
    special=[0,sign,1,sign|1,normal-1,normal,normal+1,one,sign|one,inf-1,sign|inf-1,inf,sign|inf,inf|1,inf|quiet|123,sign|inf|quiet|123]
    pairs += [(a,b) for a in special for b in special] if binary else [(a,one) for a in special]
    for c in [2.**-27,.4375,.6875,1.,1.1875,2.4375,2.**66]:
        center=bits(c,sp)
        for d in range(-8,9):
            for s in [0,sign]:pairs.append((center+d|s,one))
    while len(pairs)%lanes:pairs.append((0,one))
    rows=[];full=(1<<lanes)-1
    for start in range(0,len(pairs),lanes):
        chunk=pairs[start:start+lanes];rows.append((full,start//lanes%4,[v[0] for v in chunk],[v[1] for v in chunk],[rng.getrandbits(32 if sp else 64) for _ in range(lanes)]))
    if not million:
        for mask in [0,full,full//3,2*(full//3)]+[1<<i for i in range(lanes)]+[full^(1<<i) for i in range(lanes)]:
            for mode in range(4):rows.append((mask,mode,[(sign if i&1 else 0) if mask&(1<<i) else inf|1 for i in range(lanes)],[one if mask&(1<<i) else inf|1 for i in range(lanes)],[rng.getrandbits(32 if sp else 64) for _ in range(lanes)]))
    return rows,len(seen)
def main():
    million=sys.argv[1:]==['--mpfr-million']
    if sys.argv[1:] and not million:raise SystemExit('only --mpfr-million supported')
    folder=ROOT/'artifacts/test-state/host-atan-e'/uuid.uuid4().hex;folder.mkdir(parents=True);tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    record={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'profile':'strict baselineSSE2; noAVX/FMA; nearest-even/masked/FTZ-DAZ-off','commands':[],'variants':{}};started=time.time()
    tracked=[HERE/x for x in ['atan_e.c','atan_e.h','host_assay.c','mpfr_reference.c','check_accuracy.py','README.md']]+sorted((HERE/'upstream').glob('*'));before={str(p.relative_to(ROOT)):sha(p) for p in tracked};record['sourceSha256']=before;snapshot=folder/'sources';snapshot.mkdir()
    for p in tracked:dest=snapshot/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    try:
        def run(argv,expect=0):
            r=subprocess.run(list(map(str,argv)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=300);record['commands'].append({'argv':list(map(str,argv)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1800:]}')
            return r
        run([tools/'gcc.exe','--version'])
        for name,sp,binary in [('atanf',1,0),('atan2f',1,1),('atan2',0,1)]:
            lanes=16 if sp else 8;rows,unique=corpus(sp,binary,million);inp=folder/(name+'-input.bin')
            with inp.open('wb') as stream:
                stream.write(struct.pack('<8I',0x494c5750,1,lanes,208,len(rows),32 if sp else 64,binary,0))
                for i,(mask,mode,a,b,m) in enumerate(rows):stream.write(struct.pack('<QII'+str(lanes*3)+('I' if sp else 'Q'),i,mask,mode,*a,*b,*m))
            oracle=folder/(name+'-mpfr.exe');run([tools/'gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-DPW_SP='+str(sp),'-DPW_BINARY='+str(binary),posix(HERE/'mpfr_reference.c'),'-lmpfr','-lgmp','-o',posix(oracle)])
            previous=None
            for contraction in ['off','fast']:
                flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-psabi','-Wno-misleading-indentation','-DPW_SP='+str(sp),'-DPW_BINARY='+str(binary),'-ffp-contract='+contraction,'-I'+posix(HERE)]
                exe=folder/(name+'-'+contraction+'.exe');run([tools/'gcc.exe',*flags,posix(HERE/'host_assay.c'),posix(HERE/'atan_e.c'),'-o',posix(exe)])
                if 'INVALID_MASK_ZERO_FP_UNCHANGED' not in run([exe,'--invalid-mask']).stdout:raise ValueError('invalid mask control')
                raw=folder/(name+'-'+contraction+'.bin');run([exe,posix(inp),posix(raw)])
                if previous is not None and previous[0].read_bytes()==raw.read_bytes():result=dict(previous[1]);result['mpfrBoundByCompleteRawEqualityWith']=name+'-off'
                else:result=json.loads(run([oracle,posix(inp),posix(raw)]).stdout)
                assembly=folder/(name+'-'+contraction+'.s');run([tools/'gcc.exe',*flags,'-S',posix(HERE/'atan_e.c'),'-o',posix(assembly)]);text=assembly.read_text();packed=len(re.findall(r'\b(?:add|sub|mul|div)p[sd]\s+[^\n]*%xmm',text));imports=run([tools/'nm.exe','-u',posix(exe)]).stdout
                if not packed or re.search(r'%[yz]mm|%k[0-7]',text) or re.search(r'\b(?:atan|atanf|atan2|atan2f)\b',imports):raise ValueError('wrong arithmetic profile/scalar fallback')
                bad=folder/(name+'-'+contraction+'-wrong.bin');b=bytearray(raw.read_bytes());b[32+16+(3 if sp else 7)]^=0x40;bad.write_bytes(b);negative=run([oracle,posix(inp),posix(bad)],expect=None)
                if negative.returncode not in (6,8):raise ValueError('complete wrong-result control failed for nonnumeric reason')
                result.update({'uniqueRandomFiniteInputsOrPairs':unique,'packedSseArithmeticLines':packed,'binarySha256':sha(exe),'inputSha256':sha(inp),'rawSha256':sha(raw),'assemblySha256':sha(assembly),'completedWrongResultRejected':True});record['variants'][name+'-'+contraction]=result
                if contraction=='off':previous=(raw,result)
        if before!={str(p.relative_to(ROOT)):sha(p) for p in tracked}:raise ValueError('source changed during assay')
        record['status']='MillionInputHostAtanAlgorithmsChecked' if million else 'BoundedHostAtanAlgorithmsChecked'
    except Exception as e:record['status']='Stopped';record['error']=f'{type(e).__name__}: {e}'
    record['elapsedSeconds']=time.time()-started;(folder/'accuracy.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'artifact':str(folder/'accuracy.json'),'variants':record['variants'],'error':record.get('error')},indent=2));return int(record['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
