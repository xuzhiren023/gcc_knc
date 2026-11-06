S6-07 baseline ICE reproducers

vect-double-reduc-3.c and vect-double-reduc-7.c: original source, not reduced.
These are unchanged copies of gcc.dg/vect sources, accepted as reproducers by
the lead on 2026-11-06. Their baseline diagnostics are retained under
.work/_shared/S6-07/vect-double-reduc-{3,7}.log. Both ICE in cprop_hardreg
with knc_movhi of -1 to k1. Do not continue reducing them for this ticket.

The other 14 sources were checked after reduction. Run tools/vect_ice_check.py
with their stems to select those cases. The two original sources require the
staged .work/_shared/S6-07/tree-vect.h include directory and the original
corpus as an -iquote directory, as used by tools/vect_suite.py. They have not
been retested after copying; the original baseline compilation is the evidence.
See tests/baseline/gcc16-vect-summary.txt for options, outcomes and log paths.
