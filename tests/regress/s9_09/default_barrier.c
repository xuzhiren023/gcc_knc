/* S9-25 host check of the team barrier libgomp/config/linux/knc builds, preprocessed (gcc -E) with
   the lane's config path by tools/s9_09_checks.py host, once as libgomp is built and once with
   -DGOMP_KNC_GROUP_BARRIER.  The default is the one-level Linux barrier (config/linux/bar.h): on
   the card the per-core groups were 1.5-1.7 times slower per barrier at 60 to 240 threads (S9-09
   measurements, lead run 2026-11-11).  GOMP_KNC_BAR_GROUPS exists only in the grouped bar.h.  */
#include "bar.h"
#include "simple-bar.h"

#if defined GOMP_KNC_GROUP_BARRIER && !defined GOMP_KNC_BAR_GROUPS
#error "-DGOMP_KNC_GROUP_BARRIER does not build the per-core barrier"
#endif
#if !defined GOMP_KNC_GROUP_BARRIER && defined GOMP_KNC_BAR_GROUPS
#error "the default build has the per-core barrier, not the flat one"
#endif
