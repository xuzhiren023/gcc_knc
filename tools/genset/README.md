# Frozen unscored generality checks (S12-02)

This set is outside M4. It supplies no votes, scores, theme rankings or native
results. Inputs below are fixed before any card timing. Do not resize or select
cases after seeing comparative performance. Sources and their licence notices
remain under `.work/_shared/genset/src/`; drivers include them without rewriting
them. Keep those sources and licences with these drivers when distributing.

| Check | Frozen input and driver adaptation | Oracle |
| --- | --- | --- |
| Q1 | Ray Tracing in One Weekend v4.0.2 CC0 headers; 32x24 deterministic centre rays, depth 5, radius 0.5 sphere at (0,0,-1), radius 100 ground sphere at (0,-100.5,-1). Constructed reflection/shading replaces stochastic camera/material sampling; retains shared ownership, range iteration, virtual hit dispatch, rejection branches and recursion. Emits all 2304 unrounded colour components, including output-heavy complete-driver work. | Independent centre-hit t=0.5 and upward miss controls; complete output differential against frozen host O0. |
| Q2 | Same edition's original vec3 operators in constructed std::vector AoS loops, out=0.5*out+in. Lengths 0,1,3,4,5,7,8,9,15,16,17,257,1048576; starts offset by one element; disjoint unqualified/restricted, equal pointers, and overlap in both directions. Last size uses about 96 MiB across actual/reference buffers, larger than aggregate 7120 L2; 257 is resident. | Independent component arrays, sequential forward reference including real overlap dependencies; check every element of both buffers and guard elements. Exact dyadic input values; 130 case identities must all say PASS. Separate infinity/NaN/negative-zero class check. |
| Q3 | SC Burkardt MD dated source as staged (LGPL notice retained), original main renamed. 32 particles, 3 dimensions, mass 1, dt=.001, three compute/update steps; p[j,i]=.125*j+.0625*i, v[j,i]=.001*(i+j), initial acceleration 0. | Independent Python potential/force and velocity-Verlet equations. Compare potential, kinetic, every force, position, velocity and acceleration at every step (1158 numbers). |
| Q4 | LAPACK 3.12.0 Reference BLAS, original dgemm/lsame/xerbla. M=17 N=31 K=9, all leading dimensions 40, NN/NT/TN/TT, alpha=beta=1. A[i,j]=(i+2*j)%7-3, B[i,j]=(3*i+j)%5-2, C initially -7. Independently written C++ kernels use globals, long indices and no restrict, with i/j/k versus j/k/i traversal and identical per-element reduction order. | Every active element compared to direct dot product; every padding sentinel preserved. Integer-valued doubles give exact results; all 9600 outputs retained. Fortran buffers always disjoint; overlap is tested only in Q2's unrestricted routine. |
| Q5 | Original MIT smallpt 2008, example main renamed. 16x12 fixed primary rays from (50,52,295.6); direction=((x-7.5)/24,(y-5.5)/24-.042612,-1), normalized by original Vec. One recursive radiance call per pixel; erand48 seed words (17,23,x+16*y+1). Original global scene, AoS, methods and recursive material handling retained. Bounded extract replaces the 1024x768 example render. | Complete 576 unrounded radiance components against host O0 on the same original algorithm and POSIX erand48 stream. This differential check does not independently prove the rendering model. |
| Q6 | re2c 3.1 release pre-generated parse_etc_passwd.c, public-domain generated program; no generator build. Nine zero-padded records: root, bin (empty info), portage, empty input, truncated name, empty username, nonnumeric UID, missing newline, valid record followed by malformed record. Exact literals live in q6.c. | Predeclared accept codes 0,0,0,0,1,1,1,1,1; complete extracted fields and all error diagnostics compared exactly to the frozen host O0 capture. |

Q1/Q2 share one source family; Q1/Q5 share a rendering domain. They cannot be
counted as independent-family evidence. Q4's traversal kernels and Q2's batches
are constructed drivers, not upstream loops. Q1 is a deterministic small extract,
not the upstream stochastic camera render. No upstream implementation is copied
into compiler code. Other than renaming example entry points through inclusion,
the driver adaptations above leave third-party sources unchanged. The ray header
wrapper encloses the Ray headers in genset_rt after pre-including their system
headers to avoid Cygwin's global infinity() extension; both target compilers use
the same wrapper without macros or upstream source edits.
The smallpt driver enables POSIX/default libc declarations before its includes
for erand48 and M_PI; its algorithm and floating-point options are unchanged.

For Q1/Q3/Q5, every finite component must satisfy
`abs(actual-reference) <= 1e-10 + 1e-8*abs(reference)`. Missing, extra, nonfinite or
reordered output fails. Q2/Q4/Q6 require exact token equality; Q2 validates each
live component internally before printing PASS. Floating special values are
confined to Q2's explicit class checks; the other inputs have finite contracts.
All input initialization is runtime work; every computed result is either
materialized or checked. The host test compares O2 drivers to their references,
then rejects appended, absent and numerically corrupted outputs for every check.
Host O0 captures for Q1/Q5 are differential oracles, not independent mathematical
references. Native validation is still required; host passes do not imply it.

Build and stage from this worktree (PowerShell, no card jobs):

```powershell
$taskPython = (Get-Command python).Source
$env:PATH = "$PWD\..\_shared\toolchain\cross\bin;$PWD\..\_shared\toolchain\cygwin\bin;" + $env:PATH
& $taskPython tools/run.py --name S12-02-host --inputs tests/tools/test_genset.py tools/genset.py tools/genset -- ../_shared/toolchain/cygwin/bin/python3.12.exe tests/tools/test_genset.py
& $taskPython tools/run.py --name S12-02-stage --inputs tools/genset.py tools/genset -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/genset.py stage
```

Stage uses the installed corpus compiler prefixes: donor gcc-5.1.1 at -O2,
GCC-KNC at -O2 -march=knc, strict default FP, serial and no OpenMP. No GCC build.
Compiler/linker/lint errors remain failures, with their full cause in each fixed
build.log and status in builds.json; no optimization fallback or substitute BLAS.
Successful binaries are linted, disassembled as workload.dis for inspection,
and staged with only runtimes selected by their own compiler. All binaries,
references and logs live under `.work/_shared/S12-02/`, outside git. Host reference
outputs are frozen by the acceptance test before staging and card timing.

Lead only, after reviewing build readiness and coordinating card time:

```powershell
python tools/run.py --name S12-02-card -- python tools/genset.py lead
# Equivalent while the ticket worktree exists:
& ../_shared/S12-02/lead.ps1
```

Run the first command from the current repository/worktree after merge; the
generated convenience script records the staging worktree path. No engineer
command starts card work. The lead command launches exactly three adjacent
AB/BA/AB pairs per Q1-Q6 and full/3100/5100 profile: 108 serial launches, including
explicit failure rows for unavailable builds. All launched programs use the
corpus resident supervisor, exclusive benchmark reservation, granted topology
validation and one pinned worker; profiles select resources, not clock speed.
Each launch has a 60-second hard limit. A timeout is an infrastructure/feasibility
failure, never a speed result; do not extend or retune this set during a theme
comparison. A later long native diagnostic requires a separate parallel check.

The reused corpus launcher measures CLOCK_MONOTONIC_RAW fork-to-reap latency,
including initialization, checks, output materialization and cleanup. It transfers
output after timing. Driver clock() kernel observations are labelled separately;
Q2 includes its component checks, and Q6 includes field/diagnostic output. Do not
substitute them for complete-driver time or compare their boundaries to other
checks. The lead command checks all output against the frozen oracles after each
launch, preserves stdout/stderr and native timing/affinity metadata inline in
results.jsonl, and performs no interpretation, speedup calculation or scoring.
