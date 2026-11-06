/* One shared TU for the exact pinned musl reducer and private floor/scalbn.
 * This is source integration, not target runtime/ISA/ABI qualification. */
#include "../../math_algorithms/cos_sin_e/reducer.c"
