/* Shared library, -fPIC: tls_s is global-dynamic, tls_ls local-dynamic.  */
#include "tls.h"

TLS int tls_s = 11;
static TLS int tls_ls = 13;

int lib_get_s (void) { return tls_s; }
void lib_set_s (int v) { tls_s = v; }
int lib_get_ls (void) { return tls_ls; }
void lib_set_ls (int v) { tls_ls = v; }
