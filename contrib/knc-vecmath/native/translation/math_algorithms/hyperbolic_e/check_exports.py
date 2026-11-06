"""Compact fresh wiring of exactly the six observed hyperbolic e exports."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from check_accuracy import ROOT,HERE,environment,posix,sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--accuracy',type=Path,required=True);args=parser.parse_args()
    evidence=args.accuracy.resolve();folder=ROOT/'artifacts/test-state/host-hyperbolic-exports'/uuid.uuid4().hex
    folder.mkdir(parents=True);lib=ROOT/'native/translation/libknc_mvec';tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    production=lib/'src/e_hyperbolic_export.c'
    sources=[HERE/'export_wiring.c',HERE/'hyperbolic_e.c',production]
    expected={'_ZGVeN'+width+'v_'+name+suffix for width,suffix in(('8',''),('16','f')) for name in('sinh','cosh','tanh')}
    tracked=[*sources,HERE/'hyperbolic_e.h',lib/'include/knc_mvec_abi.h',lib/'src/e_export_adapter.h',Path(__file__),*sorted((HERE/'upstream').glob('*'))]
    report={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'commands':[],'variants':{}}
    before={str(p.relative_to(ROOT)):sha(p) for p in tracked};report['sourceSha256']=before
    snapshot=folder/'sources';snapshot.mkdir()
    for p in tracked:
        target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    try:
        def run(argv,expect=0):
            r=subprocess.run(list(map(str,argv)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=600)
            report['commands'].append({'argv':list(map(str,argv)),'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1800:]}')
            return r
        assay=json.loads(evidence.read_text())
        if assay['status']!='MillionInputHostHyperbolicAlgorithmsChecked' or assay['g5Passed'] or assay['targetQualified']:raise ValueError('invalid million accuracy evidence')
        if set(assay['variants'])!={name+suffix+'-'+mode for name in('sinh','cosh','tanh') for suffix in('','f') for mode in('off','fast')}:raise ValueError('accuracy scope')
        if any(r['uniqueFreshFiniteInputs']<1048576 or r['maxUlpBound']>1 or r['bitMergeSevereFlagMismatches'] for r in assay['variants'].values()):raise ValueError('accuracy contract')
        for path,digest in assay['sourceSha256'].items():
            if sha(ROOT/path)!=digest:raise ValueError('changed assayed source: '+path)
        report['accuracyEvidence']={'path':str(evidence.relative_to(ROOT)),'sha256':sha(evidence),'assayedSourcesUnchanged':True}
        for contraction in('off','fast'):
            flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-ffp-contract='+contraction,'-Wall','-Wextra','-Werror','-Wno-psabi','-Wno-misleading-indentation','-I'+posix(HERE),'-I'+posix(lib/'include')]
            exe=folder/('hyperbolic-wiring-'+contraction+'.exe')
            run([tools/'gcc.exe',*flags,*map(posix,sources),'-o',posix(exe)])
            output=run([exe]).stdout.strip()
            if output!='HYPERBOLIC_SOURCE_WIRING calls=384 lanes=4608 privateMaskCalls=384 inactivePoisonLanes=2304 bitFlagMxcsrMismatches=0':raise ValueError('wiring result: '+output)
            symbols=run([tools/'nm.exe','-g','--defined-only',posix(exe)]).stdout
            exports=set(re.findall(r'\b_ZGV\w+',symbols))
            if exports!=expected:raise ValueError('incorrect export scope')
            imports=run([tools/'nm.exe','-u',posix(exe)]).stdout
            if re.search(r'\b(?:sinh|cosh|tanh|exp|expm1|pow)f?\b',imports):raise ValueError('scalar math fallback import')
            report['variants'][contraction]={'calls':384,'lanes':4608,'privateMaskCalls':384,'inactivePoisonLanes':2304,'bitFlagMxcsrMismatches':0,'definedExports':sorted(exports),'scalarMathFallback':False,'binarySha256':sha(exe)}
        missing=run([tools/'gcc.exe',*flags,*map(posix,sources[:-1]),'-o',posix(folder/'missing.exe')],expect=None)
        if not missing.returncode or not all(name in missing.stderr for name in expected):raise ValueError('missing exports did not fail explicitly')
        for flag,fragment in[('-ffast-math','forbid fast-math'),('-DPW_ENABLE_NEGATIVE_CONTROL','negative controls')]:
            bad=run([tools/'gcc.exe',*flags,flag,'-c',posix(production),'-o',posix(folder/'forbidden.o')],expect=None)
            if not bad.returncode or fragment not in bad.stderr:raise ValueError('forbidden source profile accepted')
        if before!={str(p.relative_to(ROOT)):sha(p)for p in tracked}:raise ValueError('wiring source changed')
        report['status']='NewHyperbolicSourceExportsWiringChecked'
    except Exception as exc:report.update(status='Stopped',error=f'{type(exc).__name__}: {exc}')
    output=folder/'wiring.json';output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'artifact':str(output),'variants':report['variants'],'error':report.get('error')}))
    return int(report['status']=='Stopped')


if __name__=='__main__':raise SystemExit(main())
