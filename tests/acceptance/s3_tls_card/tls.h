/* S3-14 card check: __thread variables shared between donor-built and
   GCC 16-built code.  CONTROL_SHARED turns every variable into a plain global,
   which must make the check fail: it shows the check can tell per-thread
   storage from shared storage.  */

#ifdef CONTROL_SHARED
#define TLS
#else
#define TLS __thread
#endif

/* Defined in tls_donor.c (built by the donor).  */
extern TLS int tls_d;
int donor_get_d (void);
void donor_set_d (int);
int donor_get_g (void);
void donor_set_g (int);

/* Defined in tls_new.c (built by GCC 16).  */
extern TLS int tls_g;
int new_get_d (void);
void new_set_d (int);
int new_get_g (void);
void new_set_g (int);

/* Defined in the shared library tls_lib.c (built by either, -fPIC).  */
extern TLS int tls_s;
int lib_get_s (void);
void lib_set_s (int);
int lib_get_ls (void);
void lib_set_ls (int);
