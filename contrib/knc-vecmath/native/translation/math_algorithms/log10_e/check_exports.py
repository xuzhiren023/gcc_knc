"""Compact host wiring for the four new observed log10 exports only."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from check_accuracy import ROOT,HERE,environment,posix,sha
def main():
    folder=ROOT/'artifacts/test-state/host-log10-exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
    lib=ROOT/'native/translation/libknc_mvec';tools=ROOT/'.tools/knc-bootstrap/cygwin/bin'
    production=[lib/'src/e_log10f_export.c',lib/'src/e_log10_export.c',lib/'src/log10_wrappers.c']
    sources=[HERE/'export_wiring.c',HERE/'e_log10f.c',HERE/'e_log10.c',*production]
    expected={'__knc_vmath_log10f_16','__knc_vmath_log10f_4','__knc_vmath_log10_8','__knc_vmath_log10_2'}
    report={'status':'Running','hostOnly':True,'g5Passed':False,'targetQualified':False,'commands':[],'variants':{}}
    try:
        def run(args,expect=0):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=environment(),text=True,capture_output=True,timeout=90)
            report['commands'].append({'argv':list(map(str,args)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if expect is not None and r.returncode!=expect:raise ValueError(f'exit{r.returncode}: {r.stderr[-1600:]}')
            return r
        for contraction in ('off','fast'):
            flags=['-std=c11','-O3','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-mno-avx512f','-fno-fast-math','-fmath-errno','-frounding-math','-ftrapping-math','-fsignaling-nans','-Wall','-Wextra','-Werror','-Wno-psabi','-Wno-misleading-indentation','-DHAVE_FAST_FMA=0','-ffp-contract='+contraction,'-I'+posix(HERE),'-I'+posix(lib/'include')]
            exe=folder/('log10-wiring-'+contraction+'.exe');run([tools/'gcc.exe',*flags,*map(posix,sources),'-o',posix(exe)])
            text=run([exe]).stdout.strip()
            if text!='LOG10_SOURCE_WIRING calls=256 lanes=1920 bitFlagMxcsrMismatches=0':raise ValueError('incorrect wiring result: '+text)
            symbols=run([tools/'nm.exe','-g','--defined-only',posix(exe)]).stdout;exports=set(re.findall(r'\b_ZGV\w+',symbols))
            if exports!=expected:raise ValueError('incorrect export scope')
            imports=run([tools/'nm.exe','-u',posix(exe)]).stdout
            if re.search(r'\b(?:log10f?|logf?)\b',imports):raise ValueError('scalar fallback')
            report['variants'][contraction]={'calls':256,'lanes':1920,'bitFlagMxcsrMismatches':0,'definedExports':sorted(exports),'scalarMathFallback':False,'binarySha256':sha(exe)}
        missing=run([tools/'gcc.exe',*flags,*map(posix,[p for p in sources if p.name not in {'e_log10f_export.c','e_log10_export.c'}]),'-o',posix(folder/'missing.exe')],expect=None)
        if not missing.returncode or '__knc_vmath_log10f_16' not in missing.stderr or '__knc_vmath_log10_8' not in missing.stderr:raise ValueError('missing e-kernels did not fail explicitly')
        for flag,fragment in [('-ffast-math','forbid fast-math'),('-DPW_ENABLE_NEGATIVE_CONTROL','negative controls')]:
            bad=run([tools/'gcc.exe',*flags,flag,'-c',posix(production[0]),'-o',posix(folder/'forbidden.o')],expect=None)
            if not bad.returncode or fragment not in bad.stderr:raise ValueError('forbidden source profile not rejected')
        report['status']='NewLog10SourceExportsWiringChecked'
    except Exception as e:report['status']='Stopped';report['error']=f'{type(e).__name__}: {e}'
    tracked=[*sources,HERE/'log10_e.h',lib/'include/knc_mvec_abi.h',lib/'src/e_export_adapter.h',Path(__file__)]
    snapshot=folder/'sources';snapshot.mkdir()
    for p in tracked:shutil.copyfile(p,snapshot/p.name)
    report['sourceSha256']={str(p.relative_to(ROOT)):sha(p) for p in tracked};(folder/'wiring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'artifact':str(folder/'wiring.json'),'variants':report['variants'],'error':report.get('error')},indent=2))
    return int(report['status']=='Stopped')
if __name__=='__main__':raise SystemExit(main())
