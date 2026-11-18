# Lasimeri's Xeon Phi repositories: what we can use and contribute

Lead survey, 2026-11-17, from the public READMEs and selected docs of github.com/Lasimeri (86 repositories, about 25
on KNC). Read-only; nothing was cloned, built or run. Their claims are theirs (R), not our measurements.

## What exists

| Repository | What it is | Licence |
| --- | --- | --- |
| Intel-Phi-3120A, Intel-Phi-7120A | Mainline Linux 7.2.3 on KNC (30 patches), booted by a host VFIO daemon (Rust/asm), no MPSS; musl userland, dropbear ssh, hwmon sensors, KNC PMU driver (`phiperf`), DMA block devices. 7120A tree measured on a 7120A (C0, 61 cores, 1238 MHz). Linux host only (Arch). | MIT; kernel patches GPL-2.0 |
| Intel-Phi-LLVM | LLVM/Clang 23 with a `knc` target: MVEX encode/decode checked byte for byte against MPSS binutils, KNC intrinsics header, `-march=knc`. | Apache-2.0 WITH LLVM-exception (patches), MIT |
| Intel-Phi-AVX-512-ASM / -C, Intel-Phi-Offload | Host AVX-512 trapped by SIGILL and executed on the card as MVEX, bit-identical. | MIT |
| llama-phi, tridma, Intel-Phi-Stream, Intel-Phi-APL | llama.cpp with the card as a ggml matrix backend over DMA, beside a GPU. | MIT / none stated |
| Intel-Phi-Cortex(-F64, -F32-MoE) | Models trained on the card; F64 rcp/rsqrt/exp/log built from KNC's F32 estimate instructions with ULP tables. | MIT |
| Intel-Phi-AmberMD | AmberTools sander for KNC with Flang; Fortran conformance passes, sander not yet running (their G2). | GPL-3.0 |
| phifmpeg, htop-phi, glances-phi, fastfetch-phi, Flash-Dump, MVEX-OpticalFlow, VisionTrack, Blackstar | Applications and userland ports on the mainline stack. | mixed |

## Facts that matter to us

- **ABI differs from ours.** Their ADR 0002 defines "knc64-x87": float/double arguments on the stack, returns in x87
  ST0. Ours is Intel's k1om psABI (scalar FP in `zmm` lane 0, ADR-0014). Binaries do not interoperate. Their ADR
  rejected "a new GCC backend for k1om" as months of work and calls Intel's GCC 5.1 the only zmm-ABI compiler: GCC-KNC
  is that missing compiler.
- **Mainline kernel bandwidth:** their llama/APL note reports STREAM 177.9 GB/s on the 7120A under Linux 7.2.3, in
  line with our 167-185 under the MPSS uOS. Evidence that a modern kernel alone does not lift the plateau (S14-68 P12).
- **ECC capacity:** usable GDDR is 16384 MiB less 1/32 (15872 MiB), matching e820. Supports the 31/32 inline-ECC
  capacity figure S14-68 left unverified.
- **Their membw note is wrong on one point:** it says KNC has no prefetch instructions (only the SSE PREFETCHh forms
  are deleted; `vprefetch0/1/2/e*` and `clevict` exist). Its scalar loop reaches 80.5 GB/s on a 3120A at 2 threads/core.
- **PMU:** only `cycles` validated; instructions read 0 and multiplexed counts are unreliable. No GBOX counters.
- **Kernel patch 0024/0030** save the 2112-byte VPU state per task and across signals: required for any zmm-ABI
  userland on a mainline kernel.
- Their card has PCIe Gen2 x8 and on-card DMA at 3.6 GB/s host-card; ours is x4 (1.67 GB/s).

## Uses for GCC-KNC

1. PhiNix (owner moonshot): their kernel series and host daemon are the closest prior art; the blocker is the host,
   VFIO needs a Linux host and the Z840 runs Windows. Owner decision.
2. A second KNC compiler as a differential oracle: compile the same intrinsics/vector tests with Intel-Phi-LLVM and
   GCC-KNC, compare results on the card. Their ISA table is extracted from Intel 327364: keep it out of engineers'
   hands (ADR-0013); compare outputs only.
3. Corpus candidates: AmberTools sander (Fortran; gfortran-knc could reach their G2), FFmpeg/x265 (C), llama.cpp ggml
   backend (decode bandwidth, S11-09).
4. Their F64-from-F32-estimate ULP tables as a reference point for libknc_vmath accuracy (ideas and numbers, no code).

## What we could contribute (outward-facing: owner approval first)

1. GCC 16 for KNC (zmm ABI, IMCI vectorizer, libgomp, libstdc++, gfortran): their "gcc on the card" phase is not
   done, and their ADR calls this the missing piece.
2. Bandwidth facts: `vprefetch` 8/64 plus 2 threads/core reaches 185-189 GB/s read, NGO stores 171 write
   (docs/research/knc-memory-bandwidth.md), against their 80.5 scalar.
3. An ABI bridge would be a deep, owner-level choice: a knc64-x87 option in GCC-KNC, or their LLVM adopting zmm.
