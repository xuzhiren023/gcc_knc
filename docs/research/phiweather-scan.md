# What PhiWeather already knows that GCC-KNC can use

The lead read PhiWeather read only on 2026-11-03, at the owner's request ("scan the code base and you
may find scripts that's useful to us"). PhiWeather translates WRF's AVX code to IMCI assembly and
runs on the same card. This project does not depend on it: facts that matter are restated here
with their source, and nothing is copied or linked. Engineer sessions cannot read PhiWeather, so
tickets cite this note, not PhiWeather paths.

## Facts we use now

| Fact | Source in PhiWeather | Where it matters here |
|---|---|---|
| KNC's MXCSR is not SSE's: bit 21 must be 1; bits 7-12 (the SSE exception masks) and bit 20 are reserved and must be 0; PhiWeather keeps FTZ (bit 15) and DAZ (bit 6) at 0. The SSE default `ldmxcsr 0x1f80` faulted on the card. Their basis is Intel 327364-001, Table 2.15 (page 39) and B.3 (page 660) | `translator/ENTRY_RULE_KNC_MXCSR.md`, `native/translation/ABI_KNC_MXCSR.md` | Any `ldmxcsr` GCC or `libgcc` emits. Our `libgcc` only reads MXCSR, which ran on the card (S2-07). The `crtfastmath.o` that `linux-k1om.h:50` still links for `-ffast-math` writes it: S2-15 |
| Intel 327364-001 is at `https://www.intel.com/content/dam/develop/external/us/en/documents/327364001en.pdf` | same | S3-01 and S3-03 need it on this machine; the owner downloads it or allows the lead to |
| The other agent uses cores 0-29 (logical CPUs 1-120) and our shared ledger | `C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl` | Confirms our 30-59 / 121-240 mapping. PhiWeather's own `artifacts/card-coordination/jobs.jsonl` holds two old lines only |

## Useful later, not now

| What | Source | For |
|---|---|---|
| An AVX-to-IMCI mapping catalog with card status per form. Most loads and stores are marked "C": fault footprint and upper state unqualified, so it does not answer ADR-0005's page-boundary question | `docs/reviews/wrf-knc-translation-kit/03_INSTRUCTION_MAPPING_CATALOG.md`, `native/translation/03_INSTRUCTION_MAPPING_CATALOG_ADDENDUM.md` | S3-01 (IMCI forms for moves and masked tails), as a lead cross-check; S3-03 still probes the card |
| A KNC `libgfortran` build and floating-environment probes (`fenv_knc_x87`, `fenv_knc_denormal` and others) | `native/runtime/gcc14/` | E6-02 (libgfortran slice), and FP environment semantics |
| Build scripts and source locks for MPICH, OpenMP, HDF5 and NetCDF on KNC | `native/toolchains/build-knc-*.sh`, `*.lock.json` | E6 (S8): configure flags and known patches |
| Card-side affinity observation scripts | `native/knc-worker/observe-affinity*.sh` | S6 machine characterization |

Every item is a PhiWeather result for PhiWeather's needs, not a requirement here
(`CLAUDE.md`). Before a ticket relies on one, the lead restates the fact with its own check.
