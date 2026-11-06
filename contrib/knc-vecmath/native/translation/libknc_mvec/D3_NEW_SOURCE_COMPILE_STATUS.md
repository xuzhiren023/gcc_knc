# New math exports: actual Linux-target assembly, target gate open

All eleven newly implemented C translation units now generate raw Linux-target
assembly: 240,248 bytes. This is source generation only; no object, library,
card execution or G5 pass is claimed. The previous five exp/log assemblies and
the 787-source WRF census were not regenerated or rescanned.

The exact argv retains D3 BIND22, OPT and strict FP flags from the previous
source-generation route. New include paths expose the pinned trig sources.
The first source attempt stopped on DP pow's misleading-indentation warning
under `-Werror`. A separate continuation retained that diagnostic as a warning.
The upstream reducer then stopped on `-Wmaybe-uninitialized`; a final scoped
continuation demoted that diagnostic only for the reducer translation unit.
Both original failed records and all compiler logs remain retained. No BIND,
optimization, fast-math or assayed mathematical source bytes changed.

For the private reducer call, precision is exactly1 and the leading input chunk
is nonzero. Its initial jz is4; the recomputation/nonzero-limb invariant keeps
jz nonnegative before the product loop writes fq[0]. The generic compiler
warning does not prove an uninitialized production path. This scoped reasoning
does not qualify other public argument domains or replace target testing.

The connected translator reports122 unsupported names /3,457 occurrences
across the ten structurally admitted units. Leading gaps include scalar loads,
VMOVAPD/typed integer moves, broadcasts, logical operations, scalar arithmetic,
masked qword memory operations and extraction/conversion forms. The log10f
unit is separately refused because GCC split one function into hot/cold
sections; its instructions are not silently counted as admitted.

These exact queues are the ISA work list. Raw KNL output cannot run on KNC.
Aggregate evidence and compiler/source witnesses are retained under
`artifacts/test-state/knc-new-mvec-source-assembly/summary-20261022.json`.
Its three source-attempt directories are b805b46a,9057a4cd and9c9285c9.
There was no local-transfer checksum, cleanup test or benchmark work.

## Final atan and hyperbolic source increment

After the sources and complete36-export host integration were frozen, the two
new export translation units were compiled with the same D3 BIND/OPT and strict
FP policy. They produced61,585 bytes (atan) and83,303 bytes (hyperbolics) of
raw Linux-target KNL assembly. No old kernel or WRF assembly was regenerated.
The actual retained result is
`artifacts/test-state/knc-final-mvec-source-assembly/d9de5579f29942e692fc29605d9892fb/result.json`.

Atan structurally admits and supplies68 unsupported names/1,073 occurrences
with exact witnesses. Hyperbolics separately refuses a section-split function
at line3066. Neither unit emits translated assembly, links or runs on the card.
These queues are pipeline work, not target G5 qualification.

The initial new source command omitted the existing KNL deprecation diagnostic
exception and encountered misleading-indentation diagnostics. Both warnings
are now retained rather than promoted to errors, without changing source,
BIND, optimization or FP semantics. The first two stopped records remain at
237a79e0 and768f15e3. A third stopped command f3beeb89 placed a warning option
between `-o` and its output path; the compiler refused before code generation.
The fresh successful command validates that pair and preserves all failures.

The subsequent bounded cold-trap admission removes the two observed structural
refusals without changing compiler output. Hyperbolics now yields61 names/
2,011 unmapped occurrences; log10f yields37/219. See
`translator/COLD_TRAP_SECTIONS.md` and its exact queue record. General split
functions remain unsupported; this does not qualify any new instruction.
