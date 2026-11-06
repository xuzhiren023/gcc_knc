"""Compact fresh host wiring for exactly two observed tangent exports."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from check_accuracy import ROOT,HERE,environment,posix,sha
def main():
    folder=ROOT/'artifacts/test-state/host-tan-exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
    lib=ROOT/'native/translation/libknc_mvec';tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    production=[lib/'src/e_tan_export.c',lib/'src/cos_sin_reducer.c'];reducer=HERE.parent/'cos_sin_e'
    sources=[HERE/'export_wiring.c',HERE/'tan_e.c',*production]
    expected={'__knc_vmath_tanf_16','__knc_vmath_tan_8'}
    tracked=[*sources,HERE/'tan_e.h',reducer/'reducer.c',reducer/'libm.h',lib/'include/knc_mvec_abi.h',lib/'src/e_export_adapter.h',Path(__file__),*sorted((HERE/'upstream').glob('*')),*sorted((reducer/'upstream').glob('*'))]
    report={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'commands':[],'variants':{}}
    before={str(p.relative_to(ROOT)):sha(p) for p in tracked};report['sourceSha256']=before
    snapshot=folder/'sources';snapshot.mkdir()
    for p in tracked:
        target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    try:
        def run(args,expect=0):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=90)
            report['commands'].append({'argv':list(map(str,args)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1600:]}')
            return r
        evidence=ROOT/'artifacts/test-state/host-tan-e/318991b3379446daba9eba6390aa5fc2/accuracy.json'
        if sha(evidence)!='fec462280a958f0cd8e303ae53896476025e4de74f43d22b6e0caf7030fee267':raise ValueError('accuracy identity changed')
        assay=json.loads(evidence.read_text())
        if assay['status']!='MillionInputHostTanAlgorithmsChecked' or assay['g5Passed'] or assay['targetQualified']:raise ValueError('invalid accuracy evidence')
        for path,digest in assay['sourceSha256'].items():
            if sha(ROOT/path)!=digest:raise ValueError('changed assayed source: '+path)
        report['accuracyEvidence']={'path':str(evidence.relative_to(ROOT)),'sha256':sha(evidence),'assayedSourcesUnchanged':True}
        for contraction in ('off','fast'):
            flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-psabi','-Wno-misleading-indentation','-DHAVE_FAST_FMA=0','-ffp-contract='+contraction,'-I'+posix(HERE),'-I'+posix(reducer),'-I'+posix(lib/'include')]
            exe=folder/('tan-wiring-'+contraction+'.exe');run([tools/'gcc.exe',*flags,*map(posix,sources),'-o',posix(exe)])
            text=run([exe]).stdout.strip()
            if text!='TAN_SOURCE_WIRING calls=128 lanes=1536 privateMaskCalls=128 inactivePoisonLanes=768 bitFlagMxcsrMismatches=0':raise ValueError('incorrect wiring result: '+text)
            symbols=run([tools/'nm.exe','-g','--defined-only',posix(exe)]).stdout;exports=set(re.findall(r'\b_ZGV\w+',symbols))
            if exports!=expected:raise ValueError('incorrect export scope')
            imports=run([tools/'nm.exe','-u',posix(exe)]).stdout
            if re.search(r'\b(?:tan|tanf|sin|cos|sinf|cosf|sincos|sincosf|floor|scalbn)\b',imports):raise ValueError('scalar fallback/helper import')
            report['variants'][contraction]={'calls':128,'lanes':1536,'privateMaskCalls':128,'inactivePoisonLanes':768,'bitFlagMxcsrMismatches':0,'definedExports':sorted(exports),'scalarMathFallback':False,'binarySha256':sha(exe)}
        missing=run([tools/'gcc.exe',*flags,*map(posix,[p for p in sources if p.name!='e_tan_export.c']),'-o',posix(folder/'missing.exe')],expect=None)
        if not missing.returncode or not all(s in missing.stderr for s in expected if s.startswith('_ZGVe')):raise ValueError('missing e-kernels did not fail explicitly')
        missing=run([tools/'gcc.exe',*flags,*map(posix,[p for p in sources if p.name!='cos_sin_reducer.c']),'-o',posix(folder/'missing-reducer.exe')],expect=None)
        if not missing.returncode or 'phi_trig_rem_pio2' not in missing.stderr:raise ValueError('missing complete reducer did not fail explicitly')
        for flag,fragment in [('-ffast-math','forbid fast-math'),('-DPW_ENABLE_NEGATIVE_CONTROL','negative controls')]:
            bad=run([tools/'gcc.exe',*flags,flag,'-c',posix(production[0]),'-o',posix(folder/'forbidden.o')],expect=None)
            if not bad.returncode or fragment not in bad.stderr:raise ValueError('forbidden source profile not rejected')
        if before!={str(p.relative_to(ROOT)):sha(p) for p in tracked}:raise ValueError('wiring source changed')
        report['status']='NewTanSourceExportsWiringChecked'
    except Exception as e:report['status']='Stopped';report['error']=f'{type(e).__name__}: {e}'
    (folder/'wiring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'artifact':str(folder/'wiring.json'),'variants':report['variants'],'error':report.get('error')},indent=2));return int(report['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
