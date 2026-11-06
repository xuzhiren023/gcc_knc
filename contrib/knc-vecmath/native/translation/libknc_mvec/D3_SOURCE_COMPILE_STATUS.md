# D3 Linux-target source compilation status

## Current: five raw assemblies generated; unsupported forms remain

The fresh repaired source-only attempt completed all five `-S` invocations on
2026-10-22. It generated86,762 bytes of raw Linux-target KNL assembly. Every
dependency preflight and compiler exited0 with owned-job active count0; all61
preparation inputs and39 actual source/header dependencies remained byte-exact.
No object, link, generated-code execution, card contact or template qualification
occurred. Three new mnemonic names remain unknown in the active catalog, so
this result is `SourceOnlyD3AssembliesGeneratedWithUnsupportedForms`, not a
compiler/translation gate pass.

The maintained source controller is
`scripts/Compile-KncMvecD3SourcesHeaders.py`. Its single-use preparation is
`artifacts/test-state/knc-mvec-d3-source-compile/0f1845d086d345d1a85416892e16edab/preparation.json`,
SHA256`315fe65849b5daa8e08c819097fe4914c5e8888ca31932bc8ded19aca7cded34`.
The completed `compile.json` beside it has SHA256
`f2cd4496368494727cfd7e05e72cd15d5244abdcc661212df4ab182ffd17f639`.
Its exact argv retains D3 BIND22, unchanged OPT6 and every strict FP option.
Only `-Wno-error=deprecated` demotes the required KNL diagnostic; all warnings
remain in the raw logs. The explicit C system-header route is the existing
card-derived `<sysroot>/usr/include`, supplied with `-isystem`; no Cygwin headers,
compiler/source/BIND changes or shared-sysroot mutations were used.

| Fresh raw source | Assembly bytes | Assembly SHA256 |
| --- | ---: | --- |
| e_expf_export |16662|`f178a671b6fc121a2bf14825f65c51cdf7bf80ad07c20427b0b1e4f3a5469d58`|
| e_logf_export |17444|`2ba60140748d34eb15b03d41524aed9fa8e91e94c34bbd1a6ef3d796f6560479`|
| e_exp_export |24105|`2f3eb650f281e20c2f430214aa287a04a1fbe0dc286f9c7495b16cfe96a51a8a`|
| e_log_export |25682|`c9d3a55614f5a9442db1ed0bdd4791be34bd81bfd2d8d24d5f65edb7e1e4ec55`|
| exp_log_wrappers |2869|`50537468383e5239fe0bc9b28ca18a91d9039d44d2f6477e3dc051e8a3a9de66`|

The histogram scans exactly those five new outputs:3,350 instructions,
123 mnemonic names, I2041/A412/B539/C319/D0/?39. It is retained as
`histogram.json` beside the result, SHA256
`40649cedbdc96c36d4078bc331752178481617fee075fb2be27fd59a67736d3f`.
Its complete81-name non-I queue is future translation work; A/B/C categorization
does not qualify any form. No old WRF assembly was rescanned or counted.

| Unmapped name | Count | Actual operand witness / source line |
| --- | ---: | --- |
| vpgatherqq |4|`table(,%zmm12,8), %zmm13{%k2}`, e_expf_export.knl.s:148; also expf:157 and exp:273/293. |
| vpmaskmovq |34|`%ymm1, %ymm12, 64(%rsp)`, e_exp_export.knl.s:307; also other exp/log qword-mask stores. |
| vpsraq |1|`$52, %zmm15, %zmm6`, e_log_export.knl.s:478. |

These names remain `?`; no unsupported form is silently passed through or
reclassified here. The six expected narrow vector calls remain two each to
`_ZGVeN16v_expf`, `_ZGVeN16v_logf` and `_ZGVeN8v_exp`. A scoped read of these
same five assemblies finds no explicit R11 use or MXCSR load/store mnemonic.
Raw KNL assembly still must pass the future qualified translator and card
assembler/linker; it is never executable KNC evidence.

## Measured include-search repair

The new bounded probe `scripts/Probe-KncMvecD3Includes.py` first captured an
empty-input owned `-v -E` search inventory, then one explicit Linux-header
closure probe. The default search omitted `<sysroot>/usr/include` despite
`--sysroot`; it listed project paths plus GCC builtin include/include-fixed
only. The explicit route resolved31 union-input files including the actual
Linux stdint/string/math headers. Both jobs exited0/owned0. Their source/header
closure is bound into the repaired preparation, and each actual source closure
was required to be a prebound subset before its single `-S` invocation.

Probe:
`artifacts/test-state/knc-mvec-d3-includes/1c1db03930514eaeae407bbdee5dcefe/probe.json`,
SHA256`f8608a02c766c5865673dbc4d5dd6a73eabac4548595fea2c5f67ed9da71a932`.
No include overlay was needed and no shared sysroot file changed. The original
failed controller/preparation below remain unchanged and may not restart.

Next source task is to retain these unsupported-form witnesses in the rule
queue while T-A follows the approved catalog order. No G3/G5, target ABI,
target numerical or performance result follows from successful source emission.

## Preserved first attempt: failed before assembly

Attempt date:2026-10-22. This is source-generation tooling evidence only;
there is no new translator rule, target ABI/accuracy result, EM_K1OM binary or
G5 pass. Existing export/algorithm sources and previous host results remain
unchanged. No card was contacted.

The new single-use controller is
`scripts/Compile-KncMvecD3Sources.py`. It prepares the four e export translation
units and unchanged narrow wrapper with the exact D3 BIND22, unchanged OPT6,
strict FP flags and `HAVE_FAST_FMA=0`, using
`ProjectHostCompiler.command(language='c')`. Every compiler invocation uses
the existing `Retry-WrfKnlUnit.OwnedJob`, runs serially and has a300-second
limit. Actual include closure is discovered with owned `-E -M`, frozen before
the sole planned `-S`, then compared with its `-MD` closure and after hashes.
No object/link/generated-code execution is permitted and no retry is automatic.

Preparation:
`artifacts/test-state/knc-mvec-d3-source-compile/6fd73e658d6e4960a360c4ec1e08845f/preparation.json`,
SHA256`cc7da5bc3bb41b6307795c3d9c8847f43a0b9df8e8c5b3737004f5c0fd637ee1`.
Local validation authenticated31 explicit compiler/config/source/header/data/
helper/policy inputs, all five exact argv vectors, one job,300-second limit,
all22 BIND and six OPT flags exactly once, `-S` and absence of `-c`/fast-math.
The source-only preparation invoked no compiler. The subsequent run consumed
its single-use claim; never restart it or edit its used controller/source bytes.

Actual owned queries confirm `x86_64-linux-gnu` and `xgcc (GCC)14.3.0`. The
first dependency preflight, `e_expf_export`, then exited1 for two concrete causes:

- `-Werror` promoted the compiler's required `-march=knl` deprecation warning
  to `[-Werror=deprecated]`. The required BIND target itself was not changed.
- The compiler's builtin `include/stdint.h` failed at
  `#include_next <stdint.h>`, despite the declared `--sysroot`. Read-only
  inspection confirms `<sysroot>/usr/include/stdint.h` exists. This is an
  unresolved Linux-system-header search route, not evidence that the actual
  header is missing or a reason to substitute Cygwin headers.

The failed result is
`artifacts/test-state/knc-mvec-d3-source-compile/6fd73e658d6e4960a360c4ec1e08845f/compile.json`,
SHA256`880d0526495d77f43606cbd617f1475aae5eaff1d6851e5d7920fe56494bf9e2`.
`e_expf_export/dependencies.json` retains actual argv, PID44472, exit1 and
owned-job active count0. Both query jobs also terminated. The component's final
status is `Failed`, with `sourceAfterMatched=true`; the interrupted unit's
initial `Running` row is historical progress, not a live-process claim.
Zero `-S` jobs, raw assemblies, objects, links or generated executions occurred.
No histogram can be reported without any generated input.

The next action at that failure was a fresh source/preparation declaring an explicit,
authenticated Linux system-header include route and demoting only the known
KNL deprecation diagnostic while retaining every BIND/OPT/strict FP option.
Freeze the actual resolved header closure before any new `-S`; never point at
host ABI headers or mutate the configured sysroot to hide the failure. This
failure record itself did not execute or release that repair. The failed preparation,
controller, source bytes, logs and receipts stay unchanged.
