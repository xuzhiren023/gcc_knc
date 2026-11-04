/* Built by the donor: defines tls_d, and reaches GCC 16's tls_g.  */
#include "tls.h"

TLS int tls_d = 7;

int donor_get_d (void) { return tls_d; }
void donor_set_d (int v) { tls_d = v; }
int donor_get_g (void) { return tls_g; }
void donor_set_g (int v) { tls_g = v; }
