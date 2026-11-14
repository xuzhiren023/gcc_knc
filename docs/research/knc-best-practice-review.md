# KNC best practices in the official sources: what we have not adopted (2026-11-10)

A lead subagent read our flags page, ADR-0009/0013, the costs, sources, gaps and libgomp notes,
BACKLOG and CURRENT_STATE, then the sources in `knc-intrinsics-sources.md` plus two more: McCalpin
(TACC), "Native Computing and Optimization on the Intel Xeon Phi Coprocessor", IXPUG 2014,
https://www.ixpug.org/docs/IXPUG_2014_MIC_Native-new.pdf, and Corden (Intel), "FP control",
https://indico.cern.ch/event/247985/sessions/138823/attachments/427201/592962/MC_FP_control.pdf.
ICC guide pages are `https://portal.nacad.ufrj.br/online/intel/compiler_c/common/core/GUID-<id>.htm`.
Facts and references only (ADR-0013). Where each item went is in the last column.

## Not adopted or partly adopted, by expected benefit

| # | Practice | Source | Status before | Goes to |
|---|---|---|---|---|
| 1 | Prefetch for indirect access: the index stream and the gathered lines, gather prefetch hints, unrolled gather completion | ICC `-qopt-gather-scatter-unroll` (GUID-9AE10FC5-BB6C-4F22-A346-E84CDD79BF33); Rahman ch. 11; ISA pp. 303-310 | Not adopted (`knc-gather-reduce.md:87`) | BACKLOG E7-09 |
| 2 | 2 MB pages for large arrays | R08 slides 23–25; R09 p.4 ([index](knc-references.md)) | ~~THP never promotes on the card; hugetlbfs needs root~~ **Superseded S12-13:** earlier snapshot only. Card-side THP is documented for a named MPSS update; later local sweep has actual explicit huge pages. Ordinary malloc backing remains unestablished. | S12-12 G08; kernel changes only if evidence warrants |
| 3 | Spin longer before sleeping between parallel regions | R18 §§13.2.4–5 pp.59–61 | ~~Our 3 ms default is unmeasured~~ **Superseded S12-13:** current `card.h` defaults to delay 128 and 200 ms; Intel runtime advice does not establish libgomp performance. | Implemented; realistic wait/barrier follow-up is G09, later |
| 4 | Reuse large heap blocks instead of repeated mmap/munmap; allocation is serial and page zeroing slow | ICC `-qopt-malloc-options` (GUID-D0078E73-2EAA-4944-8D67-81E7D2D7CD26); Colfax | Not adopted | S9-17 (user guidance); E6-08 if an option is warranted |
| 5 | Alignment peeling and versioning at `-O2` for long loops (ICC does it by default) | ICC `-qopt-dynamic-align` (GUID-C00A2B11-E69B-4822-890F-5A35E60F5F45); McCalpin | Partly: `-O3` and `-mphinix` only (S8-09) | BACKLOG E7-10 |
| 6 | Exclusive prefetch (`vprefetche1/e0`) before stores that are not streaming | ISA pp. 641-656 | Partly: `knc_prefetch` drops the write hint (`imci.md:2132`) | BACKLOG E7-06 (amended) |
| 7 | ICC per-loop pragmas: `prefetch`, `noprefetch`, `vector nontemporal`, `vector aligned` | GUID-3A086451-4C82-4BB1-B742-FF93EBF60DA3, GUID-2B528C72-29B4-4DBC-8B91-EE4D1A03A850 | Not adopted | BACKLOG E7-11 |
| 8 | Define `__MIC__` as `-mmic` did; KNC code selects its path with it | GUID-401EDB00-AD07-4085-97EB-7C68BA42A713; CERN talk | Not adopted (`__KNC__`, `__k1om__` only) | BACKLOG E6-05b (with the intrinsics, which such code expects) |
| 9 | Opt-in accuracy controls (per-function precision, low-precision divide/sqrt) | GUID-8B4176A9-E645-4581-AF32-CEF3F2054EF3, GUID-0ADDE233-4E78-4AEC-B35A-79C580D70316, GUID-1D11B099-72A0-4DD0-A0F7-BA050887B639; Corden | Not adopted; opt-in only (ADR-0003) | BACKLOG E7-02 (amended) |
| 10 | User guidance: first-touch initialization, fewer and larger parallel regions, `nowait`, about 30 MB per thread, 1 thread per core for pure streaming (STREAM loses about 10% at 4), ICC's `-ftz` default | PRACE §13.2.2-13.2.8; McCalpin; GUID-3A5C3E47-250D-4178-A0D4-6C4ACDDA5EB8 | Partly (gaps G15 only) | S9-17 |
| 11 | No-fault padded tails (`-qopt-assume-safe-padding`) | GUID-0543CD1D-3E04-45F0-A546-555C7B1C52E0 | Parked; masked tails take most of the gain | Stays parked |

Kept as is: no `clevict` after streaming stores. ICC's default evicts (GUID-44E1F4AB-6749-4DD6-9553-75A89AC01769), but McCalpin's tuned STREAM gained 10-25% with eviction off; our behaviour matches the tuned practice.

## Adopted, and the sources agree

Two-level prefetch from `-O2` (S8-03, S9-13); L1 prefetch alongside the L2 hardware prefetcher
(S8-03); automatic streaming stores (S8-13); threads-per-core hint 4 (`knc-threads-per-core`);
64-byte alignment of statics and locals (S8-14; Fortran ALLOCATE in E6-02); spread affinity without
the OS core (S9-07); `delay` spin (S9-08); static schedule, arena and stack guidance (S9-10, S9-12);
false-sharing padding (S8-10, S9-10); `-O3` recommended (`-mphinix`); masked FP ops that raise
nothing in masked-off lanes (`sse.md` `cond_*` on KNC; `cond_fma` not enabled, minor); FMA
contraction by default (GCC's `-ffp-contract=fast`).

## Sources against our notes or defaults

1. **Denormals.** Our gaps note G6 said the VPU flushes denormals. Intel (Corden) says IMCI
   supports them and flushing comes from ICC's `-ftz`, on at every `-O` but `-O0`; our own card
   check agrees (packed add/sub/mul match x87 on subnormals, `CURRENT_STATE.md`). G6 is corrected.
   WRF's observation was likely ICC's or `-ffast-math`'s FTZ. The VPU cost of a subnormal operand is
   unmeasured: S9-16.
   **Qualification, S12-13:** R04 slides 9,18 and R27 pp.36,39,55–56
   document gradual underflow, flags and no vector FP traps. The WRF cause
   above remains an inference. Input-subnormal success does not resolve the
   current `fpu-knc.h` tiny-output-flush observation; recover the exact test,
   FZ/DAZ state and instruction before claiming agreement.
2. **L1 prefetch distance.** McCalpin uses 8, PRACE 32, we 16 (measured on a 7120P, S8-03/C5).
   No change.
3. **Thread density for bandwidth-bound code.** McCalpin finds 1 per core best for STREAM; the
   compiler keeps assuming 4 (as ICC). User guidance: S9-17.
4. **Scalar alignment.** The ICC guide says MIC data accesses must be naturally aligned
   (GUID-7E3E5C78-3F3B-4746-8C2D-A912EE1D6B38). GCC emits unaligned scalar moves (store merging,
   inline `memcpy`). The card's glibc relies on unaligned general-register loads, so it is probably
   fine, but no probe has tested it: S9-16.

## Not applicable

Offload-only settings, ICC reports, Cilk Plus, SDLT and `micvec.h`, options not available on KNC
(`-qopt-mem-layout-trans`, `-qopt-prefetch-issue-excl-hint`), IA-32 and MKL options, KNL material.
