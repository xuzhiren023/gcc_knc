# Lead card staging

T1/T2 produce temporary run outputs, removed when the runner exits. Engineers
do not stage or run card jobs. The lead can explicitly retain the binaries from
a successful check with `--stage-to` and an absolute ticket card folder:

```text
python tools/check.py t2 --compiler gcc16 --libgcc --storent --scalar-abi --vmath --stage-to <project>/.work/_shared/<ticket>
python tools/libgcc.py --stage-from <project>/.work/_shared/<ticket>
```

The export happens after all requested checks pass, before run cleanup. It copies
only `.mic` files, preserving their paths relative to runner.out. Ordinary T1/T2
commands never write to the staging folder. Use the printed `Lead card input:`
paths for card jobs. Only binaries produced by that invocation are copied; an
existing staging folder can contain older binaries from other selections.

| Former output location | Path below the explicit staging folder |
| --- | --- |
| `.work/_shared/tmp/S2-07/*-libgcc.mic` | `libgcc/*-libgcc.mic` |
| `.work/_shared/S8-13/knc-storent-publish.mic` | `storent/knc-storent-publish.mic` |
| `.work/_shared/scalar-abi/*.mic` (S3-10 native inputs) | `scalar-abi/*.mic` |
| `.work/_shared/S10-01/vecarg-*.mic` | `vector-abi/vecarg-*.mic` |
| `.work/_shared/S10-03/vmath-loop.mic` | `vmath/vmath-loop.mic` |
| Short-vector cross-links | `short-vector-cross/*.mic` |

The lead runs the staged storent binary through `tools/card_run` with its
existing publish/control arguments. Scalar and vector ABI binaries also go
through `tools/card_run`, using the exported paths. `libgcc.py --stage-from`
requires both donor and GCC16 binaries and compares their card output. It has
no fallback to the former fixed location.
