"""Compact fresh host wiring for exactly three observed atan-family exports."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from check_accuracy_v2 import ROOT,HERE,environment,posix,sha
def main():
    folder=ROOT/'artifacts/test-state/host-atan-exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
    lib=ROOT/'native/translation/libknc_mvec';tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    production=[lib/'src/e_atan_export.c']
    sources=[HERE/'export_wiring.c',HERE/'atan_e_v2.c',*production]
    expected={'__knc_vmath_atanf_16','__knc_vmath_atan2f_16','__knc_vmath_atan2_8'}
    tracked=[*sources,HERE/'atan_e.h',lib/'include/knc_mvec_abi.h',lib/'src/e_export_adapter.h',Path(__file__),*sorted((HERE/'upstream').glob('*'))]
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
        evidence=ROOT/'artifacts/test-state/host-atan-e/85b19d6b2add4ece9ec66a330ec0df17/accuracy.json'
        if sha(evidence)!='99fcededb272168215903d25af67f7b2665d541da7b6b8e83c6bfaf57e9f7fe2':raise ValueError('accuracy identity changed')
        assay=json.loads(evidence.read_text())
        if assay['status']!='MillionInputHostAtanAlgorithmsChecked' or assay['g5Passed'] or assay['targetQualified']:raise ValueError('invalid accuracy evidence')
        for path,digest in assay['sourceSha256'].items():
            if sha(ROOT/path)!=digest:raise ValueError('changed assayed source: '+path)
        report['accuracyEvidence']={'path':str(evidence.relative_to(ROOT)),'sha256':sha(evidence),'assayedSourcesUnchanged':True}
        for contraction in ('off','fast'):
            flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-psabi','-Wno-misleading-indentation','-DHAVE_FAST_FMA=0','-ffp-contract='+contraction,'-I'+posix(HERE),'-I'+posix(lib/'include')]
            exe=folder/('atan-wiring-'+contraction+'.exe');run([tools/'gcc.exe',*flags,*map(posix,sources),'-o',posix(exe)])
            text=run([exe]).stdout.strip()
            if text!='ATAN_SOURCE_WIRING calls=192 lanes=2560 privateMaskCalls=192 inactivePoisonLanes=1280 bitFlagMxcsrMismatches=0':raise ValueError('incorrect wiring result: '+text)
            symbols=run([tools/'nm.exe','-g','--defined-only',posix(exe)]).stdout;exports=set(re.findall(r'\b_ZGV\w+',symbols))
            if exports!=expected:raise ValueError('incorrect export scope')
            imports=run([tools/'nm.exe','-u',posix(exe)]).stdout
            if re.search(r'\b(?:atan|atanf|atan2|atan2f)\b',imports):raise ValueError('scalar fallback/helper import')
            report['variants'][contraction]={'calls':192,'lanes':2560,'privateMaskCalls':192,'inactivePoisonLanes':1280,'bitFlagMxcsrMismatches':0,'definedExports':sorted(exports),'scalarMathFallback':False,'binarySha256':sha(exe)}
        missing=run([tools/'gcc.exe',*flags,*map(posix,[p for p in sources if p.name!='e_atan_export.c']),'-o',posix(folder/'missing.exe')],expect=None)
        if not missing.returncode or not all(s in missing.stderr for s in expected if s.startswith('_ZGVe')):raise ValueError('missing e-kernels did not fail explicitly')
        for flag,fragment in [('-ffast-math','forbid fast-math'),('-DPW_ENABLE_NEGATIVE_CONTROL','negative controls')]:
            bad=run([tools/'gcc.exe',*flags,flag,'-c',posix(production[0]),'-o',posix(folder/'forbidden.o')],expect=None)
            if not bad.returncode or fragment not in bad.stderr:raise ValueError('forbidden source profile not rejected')
        if before!={str(p.relative_to(ROOT)):sha(p) for p in tracked}:raise ValueError('wiring source changed')
        report['status']='NewAtanSourceExportsWiringChecked'
    except Exception as e:report['status']='Stopped';report['error']=f'{type(e).__name__}: {e}'
    (folder/'wiring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'artifact':str(folder/'wiring.json'),'variants':report['variants'],'error':report.get('error')},indent=2));return int(report['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
