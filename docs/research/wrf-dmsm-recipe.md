# WRF 4.8.0 dm+sm with GCC-KNC (S12-35)

The upstream WRF host build completed with GCC-KNC commit `7a3b34430e3`.
The image's GCC 5 `mpi.mod` cannot be read by GCC-KNC 16, so this recipe
rebuilds only the four MPICH `use mpi` interface modules with GCC-KNC 16,
preserving the image's configured constants and existing link libraries.
The module/data-model, WRF build, link/ELF/dependency checks, and KNC
instruction lint passed for the staged executables and libgomp.
Native execution is a separate coordinated card check.

The primary build uses the three prebuilt MPI inputs authorized in S12-35:
`mpich-thr/libmpi.a`, `phi_thr_copy.o`, and `k17-memcpy/copy.o`.
The last object closes the helper's `phi_copy_dwords` dependency; `nm -u`
confirmed that `copy.o` has no undefined symbols. These are GCC 5.1.1-era
PhiWeather image objects, excluded from the one-compiler proof for WRF.
The image additionally wraps `memcpy`/`memmove`; this build does not.
No `memcpy_wrap.o`, `len_trim_wrap`, or other image kernel is added.

This recipe cross-builds an owned WRF tree on the Windows host using Cygwin.
PhiWeather can apply its model patches to that tree before building. The
GCC-KNC trial uses upstream WRF without those patches. Coordinate host builds
with the lead; this recipe does not start a card job.

## Compiler, libraries and environment

The installed compiler is `gcc-knc-16.2.0`, at GCC-KNC commit
`7a3b34430e3`. Keep this installation fixed throughout the clean build.
Do not use the original MPICH compiler wrappers: they inject GCC 5 target and
optimization flags. The entry below uses GCC-KNC directly, with explicit MPI
headers and static libraries.

Run the following in the Cygwin supplied by PhiWeather's knc-bootstrap:

```sh
BOOT=/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap
SHARED=/cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
TRIAL=$SHARED/wrf-trial
PREFIX=$SHARED/gcc-knc-16.2.0
MPI=$BOOT/experiments/mpich-nemesis-mmap/4cd8ccceb34a460d8841adf17c0b15b1/prefix
IMAGE=/cygdrive/c/Users/xuzhi/Documents/PhiWeather/artifacts/test-state/claude-mentor-performance-20261105
ITEM21=$IMAGE/sirocco-gf-rlh-c1b2-01/item21
export PATH="$PREFIX/bin:$BOOT/cross/bin:/usr/bin:/bin"
unset MSYSTEM MSYSTEM_PREFIX MINGW_PREFIX MSYSTEM_CHOST
export NETCDF="$TRIAL/install" NETCDF_classic=1
export NETCDF_LDFLAGS="-L$NETCDF/lib -lnetcdff -lnetcdf -lm -ldl"
unset NETCDFPAR NETCDF4 WRF_CHEM WRF_KPP WRF_HYDRO
```

`NETCDF` is the existing target static netCDF C/Fortran installation. MPI and
netCDF are external dependencies; they are not WRF objects rebuilt by this
recipe. Native Registry/preprocessor utilities use Cygwin GCC. All WRF target
C/Fortran objects use the one GCC-KNC prefix.

The original MPI is MPICH 3.4.3, built with the bootstrap GCC/GFortran 5.1.1,
`-O1 -mknc -fno-tree-vectorize`, static libraries, disabled C++, all Fortran
bindings, `ch3:nemesis:tcp`, `gforker`, and mmap shared memory. The build's
`--build` is `x86_64-pc-cygwin`, `--host` is `x86_64-linux-gnu`; the installed
objects target K1OM through its explicit cross compilers. Its wrapper records
`-lm -lpthread -lrt` as additional link dependencies.

WRF's RSL_LITE uses the MPI C interface and the legacy Fortran interface
declared by the text `mpif.h`. Include that prefix's headers; link its
`libmpifort.a` for the legacy Fortran entry points. No MPI `.mod` from GCC 5
is consumed by RSL_LITE. Firebrand spotting physics does consume `mpi.mod`;
use the GCC 16 modules prepared below before the original include directory.
Modules from different GFortran versions are not interchangeable.

The primary image MPI is the read-only prebuilt
`$ITEM21/mpich-thr/libmpi.a`, `$ITEM21/obj/thr/phi_thr_copy.o`, and
`$IMAGE/k17-memcpy/copy.o`, in that order after `$MPI/lib/libmpifort.a`.
The two helpers come from PhiWeather's image and are used read-only by
explicit lead authorization. No helper source or other model kernel is copied.
The recorded helper build uses bootstrap GCC 5.1.1 with `-mknc -O1
-fno-pic -fno-tree-vectorize -std=gnu99 -fopenmp`. Its build notes and the
reduced link both expose the `phi_copy_dwords` dependency supplied by `copy.o`.

## GCC 16 MPI modules

The scientific-sources MPICH directory contains only repository metadata
and submodule directories on this host. The complete release export and
configured sources are beside the MPI install: `$MPI/../source/mpich-3.4.3`
and `$MPI/../build/src/binding/fortran/use_mpi`. Read them without changes.
Copy only the four module sources, `mpifnoext.h`, and COPYRIGHT into an
owned module directory. This preserves the image's configure substitutions;
no MPI implementation, wrapper or library is rebuilt.

Run this with the environment above before configuring WRF. It compares
all 262 parameter definitions with installed `mpif.h`, builds the modules
in dependency order, and checks kinds, storage sizes and precision/range
against the configured data model. Stop on any mismatch.

```sh
export TRIAL
python3 - <<'PY'
from pathlib import Path
import os
import re
import shutil
import subprocess

trial = Path(os.environ['TRIAL'])
experiment = Path('/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/experiments/mpich-nemesis-mmap/4cd8ccceb34a460d8841adf17c0b15b1')
source = experiment / 'source/mpich-3.4.3'
configured = experiment / 'build/src/binding/fortran/use_mpi'
output = trial / 'dmsm-mpi'
output.mkdir(exist_ok=True)

# Preserve the original license with the authorized module-source copies.
for name in ('mpi_constants.f90', 'mpi_sizeofs.f90', 'mpi_base.f90', 'mpifnoext.h'):
    shutil.copyfile(configured / name, output / name)
shutil.copyfile(source / 'src/binding/fortran/use_mpi/mpi.f90', output / 'mpi.f90')
shutil.copyfile(source / 'COPYRIGHT', output / 'COPYRIGHT')

def parameters(path):
    text = path.read_text().upper()
    blocks = re.findall(r'PARAMETER\s*\(([^\n]+)\)', text)
    return {key: value.strip() for block in blocks
            for key, value in re.findall(r'(MPI_\w+)\s*=\s*([^,]+)', block)}

installed = parameters(experiment / 'prefix/include/mpif.h')
local = parameters(output / 'mpifnoext.h')
assert installed == local, (installed.keys() ^ local.keys(),
    [(k, installed[k], local.get(k)) for k in installed if installed[k] != local.get(k)])
assert {k: local[k] for k in ('MPI_INTEGER_KIND', 'MPI_ADDRESS_KIND', 'MPI_OFFSET_KIND', 'MPI_COUNT_KIND')} == {
    'MPI_INTEGER_KIND': '4', 'MPI_ADDRESS_KIND': '8', 'MPI_OFFSET_KIND': '8', 'MPI_COUNT_KIND': '8'}
print('Matched all', len(local), 'mpif.h parameters; integer kind 4, address/offset/count kinds 8.', flush=True)
compiler = 'k1om-mpss-linux-gfortran'
flags = ['-mphinix', '-mknc-card=7120']
subprocess.check_call([compiler, '--version'])
for name in ('mpi_constants', 'mpi_sizeofs', 'mpi_base', 'mpi'):
    subprocess.check_call([compiler] + flags + ['-c', name + '.f90'], cwd=output)

# Compile-time checks of the configured data model, without executing card code.
checks = ['kind(0) == MPI_INTEGER_KIND', 'storage_size(0) == 32',
          'storage_size(0_MPI_ADDRESS_KIND) == 64', 'storage_size(0_MPI_OFFSET_KIND) == 64',
          'storage_size(0_MPI_COUNT_KIND) == 64', 'storage_size(0.0) == 32',
          'storage_size(0.0d0) == 64', 'storage_size(.true.) == 32',
          'kind(0.0) == 4', 'kind(0.0d0) == 8', 'kind(.true.) == 4',
          'range(0) == 9', 'precision(0.0) == 6', 'range(0.0) == 37',
          'precision(0.0d0) == 15', 'range(0.0d0) == 307']
for kind, digits in ((1, 2), (2, 4), (4, 9), (8, 18)):
    checks += [f'storage_size(0_{kind}) == {kind * 8}', f'range(0_{kind}) == {digits}']
with (output / 'kind-check.f90').open('w', newline='\n') as stream:
    stream.write('module kind_check\nuse mpi\nimplicit none\n')
    for i, condition in enumerate(checks):
        stream.write(f'integer, parameter :: check_{i} = 1 / merge(1, 0, {condition})\n')
    stream.write('end module\n')
subprocess.check_call([compiler] + flags + ['-c', 'kind-check.f90'], cwd=output)
print('GCC16 kinds and storage sizes match configured MPICH data model. Modules built; no libraries replaced.', flush=True)
PY
```

Put this module directory before `$MPI/include` in `DM_FC`. The four `.mod`
files are GCC 16 inputs; their `.o` files are not added to WRF's link.
Calls still resolve through the image `libmpifort.a`. This validates the
configured data model and compilation; runtime interoperability needs the
coordinated card run.

## Source and export preparation

Use WRF v4.8.0 (`06d4240ae989cc3e50af412bb472df3d9048783c`) and all seven
submodules at the gitlinks recorded by that tag. For an owned Git checkout,
initialize the submodules recursively before exporting/building. The trial
reuses the lead's export at `$TRIAL/src/WRF-4.8.0-smpar`; its directory name
does not select the parallel configuration.

| Physics directory | Pinned commit |
| --- | --- |
| GFL | 873b414670323ae766ec4fe1f4b6b5ab891358ed |
| MYNN-EDMF | 8f8e8b59021249949c04d1686edc5a02ca325627 |
| MYNN-SFC | b66187f54a0c169e36592552634867474e603ac0 |
| TEMPO | 881614f68aa65de8f383d56139162049baf600fa |
| fire_behavior | eb7758055a5d436f022a634cae780f5512c42bb5 |
| noahmp | 5da0b241e48ecfd9a2a1bd667ed554765856d589 |
| physics_mmm | 550b5b494758ad2756394e93cb08b5709b8feb83 |

In the owned source root, normalize exported text through Cygwin Python,
preserving symlinks and file modes:

```sh
python3 - <<'PY'
from pathlib import Path
for p in Path('.').rglob('*'):
    if '.git' in p.parts or p.is_symlink() or not p.is_file():
        continue
    data = p.read_bytes()
    if b'\0' not in data and b'\r\n' in data:
        p.write_bytes(data.replace(b'\r\n', b'\n'))
PY
```

Apply these build-system changes once to a fresh upstream source tree
(already applied in the trial export). Keep existing model patches intact:

```sh
python3 - <<'PY'
from pathlib import Path
import re
def write(p, value):
    with p.open('w', newline='\n') as stream:
        stream.write(value)
p = Path('configure')
value = p.read_text()
start = value.index('    cat > ${foo}.F << EOF\n      PROGRAM GFORTRAN_VERSION_CHECK')
end = value.index('    then\n', start)
value = value[:start] + '    gcc_major=`$SFC -dumpversion | cut -d. -f1`\n    if [ "$gcc_major" -gt 9 ]\n' + value[end:]
value = value.replace('    rm ${foo} ${foo}.F 2> /dev/null\n', '')
start = value.index('# testing for location of rpc/types.h file, used in landuse')
end = value.index('# testing for netcdf4 IO features', start)
value = value[:start] + '# Cross build: RPC_TYPES selected from target headers.\n' + value[end:]
write(p, value)
p = Path('phys/Makefile')
value = p.read_text()
dirs = re.findall(r'path\s*=\s*phys/(\S+)', Path('.gitmodules').read_text())
assert len(dirs) == 7 and all((Path('phys') / d).is_dir() for d in dirs)
old = '( cd .. ; git submodule update --init --recursive )'
assert value.count(old) == 6
value = value.replace(old, '( ' + ' && '.join('test -d ' + d for d in dirs) + ' )')
write(p, '.NOTPARALLEL:\n' + value)
PY
```

The configure changes avoid executing a target Fortran program on the host
and use the target's RPC header selection. `.NOTPARALLEL` keeps physics
module generation ordered. The submodule replacement is for an export with
the seven trees already supplied; it retains upstream symlink setup.
For an exported tree inside another Git checkout, set
`GIT_CEILING_DIRECTORIES` to its containing directory, as the trial does with
`export GIT_CEILING_DIRECTORIES="$TRIAL"`.

## Architecture entry

Append the entry below to `arch/configure.defaults`, enclosed by the same
`###########################################################` separators as
the other entries. The entry is intentionally limited to `dm+sm`. On the
trial tree it replaces the earlier `GCC-KNC 16 smpar` entry. The absolute
paths match the environment above; update them if relocating the libraries.

```make
#ARCH    Linux k1om, GCC-KNC 16 dm+sm #dm+sm
#
DESCRIPTION     =       GNU ($SFC/$SCC)
DMPARALLEL      =       # 1
OMPCPP          =       # -D_OPENMP
OMP             =       # -fopenmp
OMPCC           =       # -fopenmp
SFC = k1om-mpss-linux-gfortran -static-libgcc -static-libgfortran
SCC = k1om-mpss-linux-gcc -static-libgcc
CCOMP = k1om-mpss-linux-gcc -static-libgcc
DM_FC = $(SFC) -I/cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/wrf-trial/dmsm-mpi -I/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/experiments/mpich-nemesis-mmap/4cd8ccceb34a460d8841adf17c0b15b1/prefix/include
DM_CC = $(SCC) -I/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/experiments/mpich-nemesis-mmap/4cd8ccceb34a460d8841adf17c0b15b1/prefix/include
FC              =       CONFIGURE_FC
CC              =       CONFIGURE_CC
LD              =       $(FC)
RWORDSIZE       =       CONFIGURE_RWORDSIZE
PROMOTION       =       #-fdefault-real-8
ARCH_LOCAL      =       -DNONSTANDARD_SYSTEM_SUBR  CONFIGURE_D_CTSM
# to validate WRF correctness on aarch64 against x86_64; compile with x86 this alternate ARCH_LOCAL option; able to achieve identical output model on ubuntu 18.04 with gcc 10.2 (on graviton and intel processors)
# ARCH_LOCAL      =       -DNONSTANDARD_SYSTEM_SUBR  CONFIGURE_D_CTSM -DAARCH64_X86_CORRECTNESS_FIX
CFLAGS_LOCAL = -mphinix -mknc-card=7120 -c -DRPC_TYPES=1
LDFLAGS_LOCAL = -mphinix -mknc-card=7120 -static-libgcc -static-libgfortran
CPLUSPLUSLIB    =       
ESMF_LDFLAG     =       $(CPLUSPLUSLIB)
FCOPTIM = -mphinix -mknc-card=7120 -fopt-info-vec
FCREDUCEDOPT	=       $(FCOPTIM)
FCNOOPT = -O0 -march=knc
FCDEBUG         =       # -g $(FCNOOPT) # -ggdb -fbacktrace -fcheck=bounds,do,mem,pointer -ffpe-trap=invalid,zero,overflow
FORMAT_FIXED    =       -ffixed-form
FORMAT_FREE     =       -ffree-form -ffree-line-length-none
FCSUFFIX        =       
FCCOMPAT        =       
BYTESWAPIO      =       -fconvert=big-endian -frecord-marker=4
FCBASEOPTS_NO_G =       -w $(FORMAT_FREE) $(BYTESWAPIO) $(FCCOMPAT)
FCBASEOPTS      =       $(FCBASEOPTS_NO_G) $(FCDEBUG)
MODULE_SRCH_FLAG =     
TRADFLAG        =      CONFIGURE_TRADFLAG
CPP             =      /lib/cpp CONFIGURE_CPPFLAGS
AR = k1om-mpss-linux-ar
ARFLAGS         =      ru
M4              =      m4 -G
RANLIB = k1om-mpss-linux-ranlib
RLFLAGS		=	
CC_TOOLS = gcc



LIB_LOCAL = /cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/experiments/mpich-nemesis-mmap/4cd8ccceb34a460d8841adf17c0b15b1/prefix/lib/libmpifort.a /cygdrive/c/Users/xuzhi/Documents/PhiWeather/artifacts/test-state/claude-mentor-performance-20261105/sirocco-gf-rlh-c1b2-01/item21/mpich-thr/libmpi.a /cygdrive/c/Users/xuzhi/Documents/PhiWeather/artifacts/test-state/claude-mentor-performance-20261105/sirocco-gf-rlh-c1b2-01/item21/obj/thr/phi_thr_copy.o /cygdrive/c/Users/xuzhi/Documents/PhiWeather/artifacts/test-state/claude-mentor-performance-20261105/k17-memcpy/copy.o -lm -lpthread -lrt
```

## Configure and build

From the prepared source root:

```sh
./clean -a
python3 - <<'PY'
from pathlib import Path
left = [str(p) for p in Path('.').rglob('*')
        if p.is_file() and not p.is_symlink()
        and p.suffix in ('.o', '.obj', '.a', '.mod')]
print('Post-clean objects/archives/modules:', len(left))
assert not left, left
PY
printf '1\n1\n' | ./configure -os Linux -mach k1om
./compile -j 8 em_real
test -s main/wrf.exe && test -s main/real.exe
```

Answers: option 1 is the sole K1OM entry (`dm+sm`); nesting option 1 is basic
nesting. Preserve the complete build output. Confirm `DMPARALLEL = 1`,
`OMP = -fopenmp`, and GCC 16's compatibility flags
`-fallow-argument-mismatch -fallow-invalid-boz` in `configure.wrf`.
Do not continue through a compiler ICE or change flags for individual files.
WRF's own predefined reduced/no-optimization rules remain in effect.

## The two link variants

The ordinary main links expand to these Makefile recipes, with the primary
`LIB_LOCAL` from the entry above:

```make
$(LD) -o wrf.exe $(LDFLAGS) wrf.o ../main/module_wrf_top.o $(LIBWRFLIB) $(CMAQLIB) $(LIB)
$(LD) -o real.exe $(LDFLAGS) real_em.o ../dyn_em/module_initialize_real.o $(LIBWRFLIB) $(LIB)
```

`$(LIB)` ends with the selected MPI libraries. Image MPI tail:

```sh
$MPI/lib/libmpifort.a $ITEM21/mpich-thr/libmpi.a $ITEM21/obj/thr/phi_thr_copy.o $IMAGE/k17-memcpy/copy.o -lm -lpthread -lrt
```

Original MPI tail (no image helper):

```sh
$MPI/lib/libmpifort.a $MPI/lib/libmpi.a -lm -lpthread -lrt
```

To obtain the expanded stock link command without recompiling any WRF
object, run from the source root:

```sh
WRF_ROOT=$(pwd -P)
make -C main -n -r em_wrf SOLVER=em WRF_SRC_ROOT_DIR="$WRF_ROOT" \
  LIB_LOCAL="$MPI/lib/libmpifort.a $MPI/lib/libmpi.a -lm -lpthread -lrt"
```

Execute only the printed GCC-KNC `-o wrf.exe` command from `main` (its
optional leading `time` is a shell timing wrapper), changing
its output to the absolute staging path `wrf-stockmpi.exe`. Preserve the
primary `wrf.exe` and `real.exe`. The alternate changes only MPI linkage.

Copy `libgomp.so.1.0.0` reported by
`k1om-mpss-linux-gfortran -print-file-name=libgomp.so.1.0.0` to the staging
directory as `libgomp.so.1`. GCC/Fortran support stays static. The new
OpenMP runtime is shared and must be selected before the card's GCC 5
runtime through `LD_LIBRARY_PATH`.

Run `check-wrf-links.py`, ELF/dependency checks and `tools/knc_lint` through
`tools/run.py`. Check all three executables and the staged libgomp. Native
results require a separate coordinated card run; host checks cannot supply
them. Freeze the staging directory after submission.

The link reports that `mpifcmb9_` and `mpifcmb5_` from the image
`libmpifort.a(lib_libmpifort_la-setbot.o)` have alignment 32, while WRF's
common declarations request 64. Linking succeeds, but these warnings are
retained in RUN-NOTES.md; host checks do not establish native behavior.
