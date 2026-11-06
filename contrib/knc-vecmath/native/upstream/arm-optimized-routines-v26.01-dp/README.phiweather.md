# Retained official double-precision source subset

The six original files are downloaded byte-for-byte from the official Arm
optimized-routines v26.01 resolved commit
`649ccc8411e7c4862965710f25c570d854a1483f`.
`upstream.lock.json` records each source URL, SHA256 and length. The experiments
select the offered MIT license, retain copyright notices and keep the complete
upstream license. This separate lock preserves the earlier single-precision
subset and successful experiment snapshots.

Only the original `exp_data.c`, `log_data.c` and their original configuration
header are compiled for the host experiment. The original scalar `exp.c` and
`log.c` are retained as algorithm provenance and are not linked as fallbacks.
Adapted vector arithmetic lives in `native/translation/math_algorithms/`.
`HAVE_FAST_FMA=0` selects split-c log reduction and includes its second table;
off/fast contraction of the vector expressions is tested independently.
An upstream hidden-visibility attribute has no effect on Cygwin PE; the one
attributes warning remains visible and does not become an error in the host
data build. No upstream source byte or production compiler policy is changed.
