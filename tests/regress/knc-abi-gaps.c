/* S3-15: diagnose before unnamed/MS arguments become stack slots or pointers. */
#include <stdarg.h>
typedef ELEMENT packed __attribute__((vector_size(64)));
#ifdef RECORD
typedef struct { packed value; } value_type;
#else
typedef packed value_type;
#endif

#if defined(VAR_CALL)
extern void target(int, ...);
void probe(value_type *p) { target(1, *p); }
#elif defined(VAR_GET)
void probe(value_type *p, int n, ...)
{
  va_list ap;
  va_start(ap, n);
  *p = va_arg(ap, value_type);
  va_end(ap);
}
#elif defined(MS_CALL)
extern void __attribute__((ms_abi)) target(value_type);
void probe(value_type *p) { target(*p); }
#elif defined(MS_PARAM)
void __attribute__((ms_abi)) probe(value_type x, value_type *p) { *p = x; }
#elif defined(MS_RETURN_CALL)
extern value_type __attribute__((ms_abi)) target(void);
void probe(value_type *p) { *p = target(); }
#elif defined(MS_RETURN_DEF)
value_type __attribute__((ms_abi)) probe(value_type *p) { return *p; }
#else
#error select an ABI case
#endif
