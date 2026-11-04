/* Built by GCC 16: defines tls_g, and reaches the donor's tls_d.  */
#include "tls.h"

TLS int tls_g = 9;

int new_get_d (void) { return tls_d; }
void new_set_d (int v) { tls_d = v; }
int new_get_g (void) { return tls_g; }
void new_set_g (int v) { tls_g = v; }
