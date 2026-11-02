# S0-06: GCC 16.2 fork and Cygwin timing

The shared checkout is `.work/_shared/gcc`, at tag `releases/gcc-16.2.0`
(`78d4ac73dd3`, version file `16.2.0`), on local branch `knc`.
`upstream` is `https://gcc.gnu.org/git/gcc.git`; `origin` is
`https://github.com/xuzhiren023/gcc_16_knc.git`. Nothing was pushed.
The existing checkout has `core.autocrlf=false` and `core.fileMode=false`.
Its initial status was clean, and switching to `knc` left it clean.

The case check found zero collisions among 158,889 tracked files, including
case-folded directory prefixes. Log:
`.work/_state/logs/S0_06_case_check-20261102-065801.log`.
An initial PowerShell grouping scan was cancelled before completion; the
completed check used a Python dictionary over `git ls-files -z`.

Unmodified `config.sub k1om-mpss-linux` exits zero and prints
`k1om-mpss-linux-gnu`.

The host compiler is Cygwin GCC/G++ 14.4.0, with GNU Make 4.4.1.
The runner uses the shared Cygwin `python3.12.exe` explicitly because the
extensionless `python3` launcher did not resolve in this Windows session.
`tools/s0_06_timing.py` records wall-clock seconds with `time.monotonic()`.
Build products stay in `.work/_shared/gcc-build`.

Configure options, following ADR-0001:

```
--target=x86_64-pc-cygwin --enable-languages=c,fortran
--disable-bootstrap --disable-multilib --disable-lto
```

The build command is `make -j8 all-gcc`. The incremental measurements touch
`gcc/config/i386/i386.cc`, then append a comment to
`gcc/config/i386/i386.md`, rebuilding after each. The script restores the
original `.md` contents in a `finally` block.

| Measurement | Result |
|---|---:|
| Checkout, including `.git` | 2,295,224,848 bytes (2.138 GiB) |
| Top-level configure | 60.112 seconds |
| Full `all-gcc`, C and Fortran | 2,725.762 seconds (45.43 minutes), exit 0 |
| Touch `i386.cc`, rebuild `all-gcc` | 168.536 seconds (2.81 minutes), exit 0 |
| Comment-only `i386.md` change, rebuild `all-gcc` | 264.552 seconds (4.41 minutes), exit 0 |
| Build tree | 2,474,399,661 bytes (2.304 GiB) |

Disk sizes sum logical file sizes, rather than allocated filesystem blocks.
Timing/build log: `.work/_state/logs/S0_06_timing-20261102-065354.log`.
The runner completed successfully. Peak memory was not measured. Final GCC
checkout status is clean after restoring the `.md` contents. No card tests
were requested or run; these are host build measurements.

## T1 recommendation for Milestone M0

A five-minute loop looks plausible for a narrow `i386.cc` edit: the rebuild
leaves 131.464 seconds for the rest of T1. It is marginal for `.md` work:
even the comment-only edit took 264.552 seconds, leaving just 35.448 seconds
for compiling tests, transferring them, running on the card and checking
results. A semantic pattern change may invalidate more generated output.
This run does not establish that the complete T1 loop meets its budget.

Do not lock in Cygwin as a reliably sub-five-minute development host on this
evidence. Recommend an owner-enabled WSL2 timing comparison before the M0
host decision, as provided by ADR-0001. There is no observed GCC 16.2 build
blocker here and no evidence supporting a fallback to GCC 14.4.
