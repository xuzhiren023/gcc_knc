"""Compact source-integration check for the three NEW powf exports only."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from check_accuracy import ROOT, HERE, environment, posix, sha


def main():
    folder = ROOT / "artifacts/test-state/host-powf-exports" / uuid.uuid4().hex
    folder.mkdir(parents=True)
    lib = ROOT / "native/translation/libknc_mvec"
    data = ROOT / "native/upstream/arm-optimized-routines-v26.01/math/exp2f_data.c"
    config = ROOT / "native/upstream/arm-optimized-routines-v26.01-dp/math"
    tools = ROOT / ".tools/knc-bootstrap/cygwin/bin"
    sources = [HERE / "export_wiring.c", HERE / "powf_e16.c", lib / "src/e_powf_export.c", lib / "src/powf_wrappers.c", HERE / "upstream/powf_log2_data.c", data]
    report = {"status": "Running", "hostOnly": True, "g5Passed": False, "targetQualified": False, "commands": [], "variants": {}}
    try:
        def run(argv, expect=0):
            result = subprocess.run(list(map(str, argv)), cwd=ROOT, env=environment(), text=True, capture_output=True, timeout=90)
            report["commands"].append({"argv": list(map(str, argv)), "exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            if expect is not None and result.returncode != expect:
                raise ValueError(f"unexpected exit{result.returncode}: {result.stderr[-1200:]}")
            return result
        for contraction in ("off", "fast"):
            flags = ["-std=c11", "-O3", "-march=x86-64", "-mno-avx", "-mno-avx2", "-mno-fma", "-mno-avx512f", "-fno-fast-math", "-fmath-errno", "-frounding-math", "-ftrapping-math", "-fsignaling-nans", "-DHAVE_FAST_FMA=0", "-ffp-contract="+contraction, "-Wall", "-Wextra", "-Werror", "-Wno-error=attributes", "-Wno-psabi", "-I"+posix(HERE), "-I"+posix(lib / "include"), "-I"+posix(config)]
            exe = folder / ("powf-wiring-"+contraction+".exe")
            run([tools / "gcc.exe", *flags, *map(posix, sources), "-o", posix(exe)])
            text = run([exe]).stdout.strip()
            if text != "POWF_SOURCE_WIRING calls=192 lanes=1792 bitFlagMxcsrMismatches=0":
                raise ValueError("wiring diagnostic mismatch: "+text)
            symbols = run([tools / "nm.exe", "-g", "--defined-only", posix(exe)]).stdout
            exports = sorted(set(re.findall(r"\b_ZGV\w+", symbols)))
            if exports != sorted(["__knc_vmath_powf_16", "__knc_vmath_powf_8", "__knc_vmath_powf_4"]):
                raise ValueError("defined export scope differs")
            imports = run([tools / "nm.exe", "-u", posix(exe)]).stdout
            if re.search(r"\b(?:powf?|log2?f?|exp2?f?)\b", imports):
                raise ValueError("scalar math import")
            report["variants"][contraction] = {"calls": 192, "lanes": 1792, "bitFlagMxcsrMismatches": 0, "definedExports": exports, "binarySha256": sha(exe), "scalarMathFallback": False}
        # Linking the new narrow wrappers without their e kernel must fail.
        result = run([tools / "gcc.exe", *flags, *map(posix, [p for p in sources if p.name != "e_powf_export.c"]), "-o", posix(folder / "missing.exe")], expect=None)
        if not result.returncode or "__knc_vmath_powf_16" not in result.stderr:
            raise ValueError("missing e-kernel did not fail explicitly")
        report["missingKernelRejected"] = True
        for flag in ("-ffast-math", "-DPW_ENABLE_NEGATIVE_CONTROL"):
            result = run([tools / "gcc.exe", *flags, flag, "-c", posix(lib / "src/e_powf_export.c"), "-o", posix(folder / "forbidden.o")], expect=None)
            if not result.returncode or "production powf export forbids" not in result.stderr:
                raise ValueError("forbidden source profile was not rejected")
        report["status"] = "NewPowfSourceExportsWiringChecked"
    except Exception as error:
        report["status"] = "Stopped"
        report["error"] = f"{type(error).__name__}: {error}"
    tracked = [*sources, HERE / "powf_e16.h", lib / "include/knc_mvec_abi.h", config / "math_config.h", Path(__file__)]
    report["sourceSha256"] = {str(path.relative_to(ROOT)): sha(path) for path in tracked}
    snapshot = folder / "sources";snapshot.mkdir()
    for path in tracked:
        shutil.copyfile(path,snapshot / path.name)
    (folder / "wiring.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status": report["status"], "artifact": str(folder / "wiring.json"), "variants": report["variants"], "error": report.get("error")},indent=2))
    return 0 if report["status"] == "NewPowfSourceExportsWiringChecked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
