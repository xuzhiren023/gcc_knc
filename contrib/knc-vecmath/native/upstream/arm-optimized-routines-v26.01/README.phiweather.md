# Retained official Arm source subset

These original files are byte-exact downloads from the official
ARM-software/optimized-routines repository, pinned by `upstream.lock.json`.
Release v26.01 resolves to commit
`649ccc8411e7c4862965710f25c570d854a1483f`.
No file in the upstream subset is compiled or modified by the local vector
experiments. Adaptations live separately in
`native/translation/math_algorithms/`.

Upstream offers MIT OR Apache-2.0 WITH LLVM-exception; these adaptations select
MIT and preserve upstream copyrights. The complete offered license text is
retained in `LICENSE`. The subset supplies provenance for exact tables and
coefficients, not an inherited accuracy, ABI or hardware claim.
